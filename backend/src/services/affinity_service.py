import math
from datetime import datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from src.models.affinity import UserTopicAffinity
from src.models.spree import Spree, SpreeType


def normalize_topic(topic: str) -> str:
    """Normalize topic to lowercase trimmed string, stripping leading '#' if present, capped at 100 chars."""
    if not topic:
        return ""
    norm = str(topic).strip().lower()
    if norm.startswith("#"):
        norm = norm.lstrip("#").strip()
    return norm[:100]


def extract_spree_topics(spree: Spree) -> List[str]:
    """Extract unique normalized topic strings from a Spree's category and tags."""
    if not spree:
        return []
    topics: List[str] = []
    category = getattr(spree, "category", None)
    if category:
        cat_norm = normalize_topic(category)
        if cat_norm and cat_norm not in topics:
            topics.append(cat_norm)

    tags = getattr(spree, "tags", None)
    if tags:
        if isinstance(tags, str):
            tags_str = tags.strip()
            if tags_str.startswith("[") and tags_str.endswith("]"):
                try:
                    import json
                    parsed = json.loads(tags_str)
                    if isinstance(parsed, list):
                        tags = parsed
                    else:
                        tags = [tags_str]
                except Exception:
                    tags = [tags_str]
            else:
                tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        if isinstance(tags, list):
            for tag in tags:
                if tag is not None:
                    t_norm = normalize_topic(str(tag))
                    if t_norm and t_norm not in topics:
                        topics.append(t_norm)

    return topics


class AffinityService:
    def __init__(self, db: Session):
        self.db = db

    def get_affinity(self, user_id: str, topic: str) -> Optional[UserTopicAffinity]:
        norm = normalize_topic(topic)
        if not norm or not user_id:
            return None
        return (
            self.db.query(UserTopicAffinity)
            .filter(
                UserTopicAffinity.user_id == user_id,
                UserTopicAffinity.topic == norm,
            )
            .first()
        )

    def get_user_affinities(self, user_id: str) -> Dict[str, float]:
        """Return dict of {topic: score} for a given user."""
        if not user_id:
            return {}
        records = (
            self.db.query(UserTopicAffinity)
            .filter(UserTopicAffinity.user_id == user_id)
            .all()
        )
        return {r.topic: float(r.score) for r in records}

    def update_topic_score(self, user_id: str, topic: str, delta: float) -> Optional[UserTopicAffinity]:
        """
        Increment or decrement user topic affinity score by delta.
        Enforces a minimum floor of 0.0. Concurrency-safe against unique constraint collisions.
        """
        norm = normalize_topic(topic)
        if not norm or not user_id:
            return None

        record = self.get_affinity(user_id, norm)
        now = datetime.now(timezone.utc)

        if record:
            new_score = max(0.0, round(record.score + delta, 4))
            record.score = new_score
            record.updated_at = now
        else:
            new_score = max(0.0, round(delta, 4))
            record = UserTopicAffinity(
                user_id=user_id,
                topic=norm,
                score=new_score,
                updated_at=now,
            )
            self.db.add(record)

        try:
            self.db.commit()
            self.db.refresh(record)
            return record
        except IntegrityError:
            self.db.rollback()
            try:
                existing = self.get_affinity(user_id, norm)
                if existing:
                    existing.score = max(0.0, round(existing.score + delta, 4))
                    existing.updated_at = now
                    self.db.commit()
                    self.db.refresh(existing)
                    return existing
            except Exception:
                self.db.rollback()
                raise
            raise
        except Exception:
            self.db.rollback()
            raise

    def update_topics_score(self, user_id: str, topics: List[str], delta: float) -> None:
        """Update affinity scores for multiple topics atomically in a single transaction."""
        if not user_id or not topics:
            return

        unique_topics = set()
        for t in topics:
            norm = normalize_topic(t)
            if norm:
                unique_topics.add(norm)

        if not unique_topics:
            return

        now = datetime.now(timezone.utc)
        try:
            records = (
                self.db.query(UserTopicAffinity)
                .filter(
                    UserTopicAffinity.user_id == user_id,
                    UserTopicAffinity.topic.in_(list(unique_topics)),
                )
                .all()
            )
            record_map = {r.topic: r for r in records}

            for norm in unique_topics:
                if norm in record_map:
                    rec = record_map[norm]
                    rec.score = max(0.0, round(rec.score + delta, 4))
                    rec.updated_at = now
                else:
                    new_score = max(0.0, round(delta, 4))
                    new_rec = UserTopicAffinity(
                        user_id=user_id,
                        topic=norm,
                        score=new_score,
                        updated_at=now,
                    )
                    self.db.add(new_rec)
                    record_map[norm] = new_rec

            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            # On concurrent race condition, fall back safely topic-by-topic
            for norm in unique_topics:
                self.update_topic_score(user_id, norm, delta)
        except Exception:
            self.db.rollback()
            raise

    def process_view_signal(
        self,
        user_id: Optional[str],
        spree: Spree,
        watch_duration: float = 0.0,
        completed: bool = False,
    ) -> None:
        """
        Process view engagement signal:
        - If video watched >= 80% or completed == True: Increment user's score by +2.0 points.
        - If video skipped (< 3.0 seconds): Decrement user's score by -1.0 point (minimum floor 0.0).
        """
        if not user_id or not spree:
            return

        if math.isnan(watch_duration) or math.isinf(watch_duration):
            return
        watch_duration = max(0.0, float(watch_duration))

        topics = extract_spree_topics(spree)
        if not topics:
            return

        is_high_completion = completed is True
        if not is_high_completion and spree.duration and spree.duration > 0:
            if (watch_duration / spree.duration) >= 0.8:
                is_high_completion = True

        if is_high_completion:
            self.update_topics_score(user_id, topics, +2.0)
        elif watch_duration < 3.0:
            if getattr(spree, "type", None) != SpreeType.PHOTO:
                self.update_topics_score(user_id, topics, -1.0)

    def process_clap_signal(self, user_id: Optional[str], spree: Spree) -> None:
        """Clap signal: +1.5 points."""
        if not user_id or not spree:
            return
        topics = extract_spree_topics(spree)
        if topics:
            self.update_topics_score(user_id, topics, +1.5)

    def process_save_signal(self, user_id: Optional[str], spree: Spree) -> None:
        """Save signal: +3.0 points."""
        if not user_id or not spree:
            return
        topics = extract_spree_topics(spree)
        if topics:
            self.update_topics_score(user_id, topics, +3.0)

    def process_share_signal(self, user_id: Optional[str], spree: Spree) -> None:
        """Share signal: +5.0 points."""
        if not user_id or not spree:
            return
        topics = extract_spree_topics(spree)
        if topics:
            self.update_topics_score(user_id, topics, +5.0)
