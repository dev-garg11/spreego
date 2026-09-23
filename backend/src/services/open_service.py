from datetime import datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy.orm import Session, joinedload
from src.models.open import (
    DEFAULT_SCORING_CONFIG,
    Open,
    OpenParticipant,
    OpenStatus,
    OpenSubmission,
    OpenType,
)
from src.models.spree import Spree
from src.models.user import User
from src.repositories.open_repository import OpenRepository
from src.repositories.spree_repository import SpreeRepository
from src.services.feed_ranking_service import (
    FeedRankingService,
    ScoredSpreeItem,
    SpreeEngagementStats,
)
from src.validations.feed_schemas import (
    FeedCreatorInfo,
    FeedEngagementMetrics,
    FeedSpreeResponse,
)
from src.validations.open_schemas import (
    CreateOpenRequest,
    OpenRankingItem,
)


class OpenService:
    def __init__(self, db: Session):
        self.db = db
        self.open_repo = OpenRepository(db)
        self.spree_repo = SpreeRepository(db)
        self.feed_ranking_service = FeedRankingService(db)

    @staticmethod
    def _to_utc(dt: Optional[datetime]) -> datetime:
        if dt is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def create_open(self, creator_id: str, payload: CreateOpenRequest) -> Open:
        user = self.db.query(User).filter(User.id == creator_id).first()
        if user and not user.is_active:
            raise PermissionError("User account is deactivated.")

        now = datetime.now(timezone.utc)
        start_at = self._to_utc(payload.start_at) if payload.start_at else now
        end_at = self._to_utc(payload.end_at)

        if end_at <= start_at:
            raise ValueError("end_at must be strictly after start_at.")

        scoring_config = (
            payload.scoring_config
            if payload.scoring_config
            else dict(DEFAULT_SCORING_CONFIG)
        )

        open_obj = Open(
            creator_id=creator_id,
            type=payload.type,
            title=payload.title,
            description=payload.description,
            cover_image_url=payload.cover_image_url,
            rules=payload.rules,
            start_at=start_at,
            end_at=end_at,
            status=payload.status or OpenStatus.ACTIVE,
            reward_info=payload.reward_info,
            max_participants=payload.max_participants,
            scoring_config=scoring_config,
        )
        return self.open_repo.create(open_obj)

    def get_open(self, open_id: str) -> Open:
        open_obj = self.open_repo.get_by_id(open_id)
        if not open_obj:
            raise LookupError("Open not found.")
        return open_obj

    def list_opens(
        self,
        open_type: Optional[OpenType] = None,
        open_status: Optional[OpenStatus] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Open]:
        return self.open_repo.get_opens(
            open_type=open_type,
            open_status=open_status,
            skip=skip,
            limit=limit,
        )

    def join_open(self, open_id: str, current_user: User) -> OpenParticipant:
        if not current_user or not current_user.is_active:
            raise PermissionError("User account is deactivated.")

        open_obj = self.get_open(open_id)

        # Status validation
        if open_obj.status == OpenStatus.COMPLETED:
            raise ValueError("Cannot join a completed Open.")
        if open_obj.status == OpenStatus.CANCELLED:
            raise ValueError("Cannot join a cancelled Open.")
        if open_obj.status == OpenStatus.DRAFT:
            raise ValueError("Cannot join a draft Open.")
        if open_obj.status != OpenStatus.ACTIVE:
            raise ValueError(f"Cannot join an Open with status '{open_obj.status}'.")

        # Expiration / timing check
        now = datetime.now(timezone.utc)
        start = self._to_utc(open_obj.start_at)
        end = self._to_utc(open_obj.end_at)

        if now < start:
            raise ValueError("Cannot join an Open that has not started yet.")
        if now > end:
            raise ValueError("Cannot join an expired Open.")

        # Max participants check
        if open_obj.max_participants is not None:
            current_count = self.open_repo.count_participants(open_id)
            if current_count >= open_obj.max_participants:
                raise ValueError("Open has reached maximum participant limit.")

        # Duplicate join check
        existing = self.open_repo.get_participant(open_id=open_id, user_id=current_user.id)
        if existing:
            raise ValueError("You have already joined this Open.")

        return self.open_repo.add_participant(open_id=open_id, user_id=current_user.id)

    def submit_spree(self, open_id: str, spree_id: str, current_user: User) -> OpenSubmission:
        if not current_user or not current_user.is_active:
            raise PermissionError("User account is deactivated.")

        open_obj = self.get_open(open_id)

        # Status validation
        if open_obj.status != OpenStatus.ACTIVE:
            raise ValueError("Cannot submit to an inactive Open.")

        # Expiration / timing check
        now = datetime.now(timezone.utc)
        start = self._to_utc(open_obj.start_at)
        end = self._to_utc(open_obj.end_at)

        if now < start:
            raise ValueError("Cannot submit to an Open that has not started yet.")
        if now > end:
            raise ValueError("Cannot submit to an expired Open.")

        # Spree lookup
        spree = self.spree_repo.get_by_id(spree_id)
        if not spree:
            raise LookupError("Spree not found.")

        # Ownership validation
        if spree.creator_id != current_user.id:
            raise PermissionError("You can only submit Sprees that you created.")

        # Duplicate submission check
        existing = self.open_repo.get_submission_by_spree(open_id=open_id, spree_id=spree_id)
        if existing:
            raise ValueError("This Spree has already been submitted to this Open.")

        # Auto-join if user has not joined as participant yet
        if not self.open_repo.get_participant(open_id=open_id, user_id=current_user.id):
            if open_obj.max_participants is not None:
                current_count = self.open_repo.count_participants(open_id)
                if current_count >= open_obj.max_participants:
                    raise ValueError("Open has reached maximum participant limit.")
            try:
                self.open_repo.add_participant(open_id=open_id, user_id=current_user.id)
            except (ValueError, IntegrityError):
                pass

        # Calculate initial score based on existing metrics
        stats_map = self.feed_ranking_service._batch_aggregate_engagement([spree_id])
        stats = stats_map.get(spree_id, SpreeEngagementStats())
        initial_score = self._compute_score(stats, open_obj.scoring_config)

        return self.open_repo.add_submission(
            open_id=open_id,
            user_id=current_user.id,
            spree_id=spree_id,
            score=initial_score,
        )

    def get_feed(self, open_id: str, skip: int = 0, limit: int = 20) -> List[FeedSpreeResponse]:
        open_obj = self.get_open(open_id)

        # Query submissions strictly for this Open
        submissions = self.open_repo.get_submissions_for_open(open_id=open_id, skip=skip, limit=limit)
        if not submissions:
            return []

        spree_ids = [sub.spree_id for sub in submissions]
        batch_stats = self.feed_ranking_service._batch_aggregate_engagement(spree_ids)

        sprees = (
            self.db.query(Spree)
            .options(joinedload(Spree.creator).joinedload(User.profile))
            .filter(Spree.id.in_(spree_ids))
            .all()
        )
        spree_map = {s.id: s for s in sprees}

        feed_items: List[FeedSpreeResponse] = []
        for sub in submissions:
            spree = spree_map.get(sub.spree_id)
            if not spree:
                continue
            stats = batch_stats.get(sub.spree_id, SpreeEngagementStats())
            score = self._compute_score(stats, open_obj.scoring_config)
            scored_item = ScoredSpreeItem(
                spree=spree,
                score=score,
                engagement=stats,
                is_buzzer_active=False,
                buzzer_multiplier=1.0,
                breakdown={},
            )
            feed_resp = self.feed_ranking_service._to_feed_response(scored_item)
            feed_items.append(feed_resp)

        return feed_items

    def get_ranking(self, open_id: str) -> List[OpenRankingItem]:
        open_obj = self.get_open(open_id)

        # Retrieve all submissions for this Open to compute real-time dynamic ranking
        submissions = self.open_repo.get_submissions_for_open(open_id=open_id, skip=0, limit=10000)
        if not submissions:
            return []

        spree_ids = [sub.spree_id for sub in submissions]
        batch_stats = self.feed_ranking_service._batch_aggregate_engagement(spree_ids)

        sprees = (
            self.db.query(Spree)
            .options(joinedload(Spree.creator).joinedload(User.profile))
            .filter(Spree.id.in_(spree_ids))
            .all()
        )
        spree_map = {s.id: s for s in sprees}

        scored_entries = []
        for sub in submissions:
            spree = spree_map.get(sub.spree_id)
            if not spree:
                continue
            stats = batch_stats.get(sub.spree_id, SpreeEngagementStats())
            score = self._compute_score(stats, open_obj.scoring_config)
            scored_entries.append({
                "submission": sub,
                "spree": spree,
                "stats": stats,
                "score": score,
            })

        # ponytail: in-memory ranking fetches up to 10k submissions; use async redis sorted set or indexed score aggregation when scale exceeds 10k
        # Order by score descending, tie-break by submission timestamp ascending, then submission id
        scored_entries.sort(
            key=lambda x: (
                -x["score"],
                self._to_utc(x["submission"].created_at),
                str(x["submission"].id or ""),
            )
        )

        ranking_items: List[OpenRankingItem] = []
        for idx, entry in enumerate(scored_entries):
            rank = idx + 1
            sub = entry["submission"]
            sub.score = entry["score"]
            sub.rank = rank

            spree = entry["spree"]
            stats = entry["stats"]

            creator_info = None
            if spree and spree.creator:
                prof = getattr(spree.creator, "profile", None)
                creator_info = FeedCreatorInfo(
                    id=spree.creator.id,
                    username=prof.username if prof else None,
                    full_name=prof.full_name if prof else None,
                    avatar_url=prof.avatar_url if prof else None,
                )

            metrics = FeedEngagementMetrics(
                views_count=stats.views_count,
                completed_views_count=stats.completed_views_count,
                watch_completion_rate=stats.watch_completion_rate,
                claps_count=stats.claps_count,
                comments_count=stats.comments_count,
                saves_count=stats.saves_count,
                shares_count=stats.shares_count,
            )

            spree_resp = None
            if spree:
                scored_item = ScoredSpreeItem(
                    spree=spree,
                    score=entry["score"],
                    engagement=stats,
                    is_buzzer_active=False,
                    buzzer_multiplier=1.0,
                    breakdown={},
                )
                spree_resp = self.feed_ranking_service._to_feed_response(scored_item)

            ranking_items.append(
                OpenRankingItem(
                    rank=rank,
                    score=entry["score"],
                    submission_id=sub.id,
                    spree_id=sub.spree_id,
                    user_id=sub.user_id,
                    creator_id=sub.user_id,
                    creator=creator_info,
                    spree=spree_resp,
                    spree_title=spree.title if spree else None,
                    metrics=metrics,
                    created_at=sub.created_at,
                )
            )

        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return ranking_items

    def _compute_score(
        self,
        stats: SpreeEngagementStats,
        scoring_config: Optional[Dict[str, float]],
    ) -> float:
        import math
        config = scoring_config if scoring_config is not None else DEFAULT_SCORING_CONFIG
        metric_map = {
            "claps": stats.claps_count,
            "claps_count": stats.claps_count,
            "views": stats.views_count,
            "views_count": stats.views_count,
            "shares": stats.shares_count,
            "shares_count": stats.shares_count,
            "comments": stats.comments_count,
            "comments_count": stats.comments_count,
            "saves": stats.saves_count,
            "saves_count": stats.saves_count,
            "completion": stats.completed_views_count,
            "completed_views": stats.completed_views_count,
            "completed_views_count": stats.completed_views_count,
            "completion_rate": stats.watch_completion_rate,
            "watch_completion_rate": stats.watch_completion_rate,
        }
        score = 0.0
        for key, weight in config.items():
            try:
                w = float(weight)
                if not math.isfinite(w) or w < 0:
                    continue
            except (ValueError, TypeError):
                continue
            clean_key = str(key).strip().lower()
            val = None
            if clean_key in metric_map:
                val = metric_map[clean_key]
            elif hasattr(stats, clean_key) and not clean_key.startswith("_"):
                attr = getattr(stats, clean_key)
                if isinstance(attr, (int, float)):
                    val = attr
            if val is not None:
                try:
                    score += w * float(val)
                except (ValueError, TypeError):
                    continue
        return round(score, 4)
