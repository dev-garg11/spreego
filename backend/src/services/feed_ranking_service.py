import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session, contains_eager, joinedload
from src.models.affinity import UserTopicAffinity
from src.models.buzzer import BuzzerCampaign, BuzzerStatus
from src.models.engagement import (
    SpreeClap,
    SpreeComment,
    SpreeSave,
    SpreeShare,
    SpreeView,
)
from src.models.follow import Follow
from src.models.spree import Spree, SpreeType, SpreeVisibility
from src.models.user import User
from src.repositories.buzzer_repository import BuzzerRepository
from src.services.affinity_service import extract_spree_topics
from src.validations.feed_schemas import (
    FeedCreatorInfo,
    FeedEngagementMetrics,
    FeedSpreeResponse,
)


@dataclass
class SpreeEngagementStats:
    views_count: int = 0
    completed_views_count: int = 0
    watch_completion_rate: float = 0.0
    claps_count: int = 0
    comments_count: int = 0
    saves_count: int = 0
    shares_count: int = 0


@dataclass
class SpreeCandidate:
    spree: Spree
    engagement: SpreeEngagementStats
    buzzer_multiplier: float = 1.0
    is_buzzer_active: bool = False
    is_following_creator: bool = False
    topic_affinity_boost: float = 0.0
    user_topic_affinities: Optional[Dict[str, float]] = None


@dataclass
class ScoredSpreeItem:
    spree: Spree
    score: float
    engagement: SpreeEngagementStats
    is_buzzer_active: bool
    buzzer_multiplier: float
    breakdown: Dict[str, float]


class FeedRankingStrategy(ABC):
    """Abstract base class for pluggable discovery ranking strategies (e.g. Heuristic, ML model)."""

    @abstractmethod
    def score_candidate(
        self,
        candidate: SpreeCandidate,
        now: datetime,
    ) -> ScoredSpreeItem:
        """Calculate ranking score for a candidate Spree based on real signals."""
        pass

    def apply_anti_fatigue(
        self,
        items: List[ScoredSpreeItem],
        max_consecutive: int = 2,
    ) -> List[ScoredSpreeItem]:
        """
        Anti-fatigue check: ensure diverse ranking so a single creator
        doesn't completely monopolize consecutive feed items.
        Allows at most `max_consecutive` consecutive items from the same creator
        when candidates from other creators are available.
        """
        if len(items) <= max_consecutive or max_consecutive <= 0:
            return items

        remaining = list(items)
        result: List[ScoredSpreeItem] = []

        while remaining:
            last_creators = [
                r.spree.creator_id
                for r in result[-max_consecutive:]
                if r.spree and r.spree.creator_id
            ]

            must_diversify = (
                len(last_creators) == max_consecutive
                and len(set(last_creators)) == 1
            )

            chosen_idx = None
            if must_diversify:
                banned_creator = last_creators[0]
                for i, cand in enumerate(remaining):
                    cand_creator = cand.spree.creator_id if cand.spree else None
                    if cand_creator != banned_creator:
                        chosen_idx = i
                        break

            if chosen_idx is None:
                chosen_idx = 0

            result.append(remaining.pop(chosen_idx))

        return result

    def rank_candidates(
        self,
        candidates: List[SpreeCandidate],
        now: datetime,
    ) -> List[ScoredSpreeItem]:
        """Rank candidates in descending order of score with deterministic tie-breaking and anti-fatigue diversity."""
        scored = [self.score_candidate(c, now) for c in candidates]

        def sort_key(item: ScoredSpreeItem):
            ts = ensure_utc(item.spree.created_at).timestamp() if item.spree and item.spree.created_at else 0.0
            score = item.score if not (math.isnan(item.score) or math.isinf(item.score)) else 0.0
            return (score, ts, str(item.spree.id or ""))

        scored.sort(key=sort_key, reverse=True)
        max_consecutive = getattr(self, "max_consecutive_creator", 2)
        return self.apply_anti_fatigue(scored, max_consecutive=max_consecutive)


def ensure_utc(dt: Optional[datetime] = None) -> datetime:
    """Normalize datetime to UTC timezone-aware datetime."""
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class HeuristicFeedRankingStrategy(FeedRankingStrategy):
    """
    Default heuristic scoring engine combining:
    - Freshness: exponential decay based on age in hours.
    - Engagement: claps, comments, saves, shares with weighted signals.
    - Watch Quality: views count + watch completion ratio.
    - Creator Affinity: boost if requesting user follows the Spree's creator.
    - Buzzer Multiplier: boost multiplier if Spree has an active Buzzer campaign.
    """

    def __init__(
        self,
        weight_clap: float = 2.0,
        weight_comment: float = 3.0,
        weight_save: float = 4.0,
        weight_share: float = 5.0,
        weight_view: float = 0.5,
        weight_completion: float = 10.0,
        affinity_boost: float = 25.0,
        base_score: float = 10.0,
        half_life_hours: float = 24.0,
        max_consecutive_creator: int = 2,
    ):
        self.weight_clap = weight_clap
        self.weight_comment = weight_comment
        self.weight_save = weight_save
        self.weight_share = weight_share
        self.weight_view = weight_view
        self.weight_completion = weight_completion
        self.affinity_boost = affinity_boost
        self.base_score = base_score
        self.half_life_hours = max(0.1, half_life_hours)
        self.max_consecutive_creator = max_consecutive_creator

    def compute_topic_affinity_boost(
        self,
        spree: Spree,
        user_affinities: Optional[Dict[str, float]],
    ) -> float:
        """
        Compute topic_affinity_boost = sum(user_topic_score for topic in spree_topics).
        Looks up the user's affinity scores for candidate Spree's category and tags.
        """
        if not user_affinities or not spree:
            return 0.0
        spree_topics = extract_spree_topics(spree)
        return max(0.0, float(sum(user_affinities.get(t, 0.0) for t in spree_topics)))

    def score_candidate(
        self,
        candidate: SpreeCandidate,
        now: datetime,
    ) -> ScoredSpreeItem:
        spree = candidate.spree
        eng = candidate.engagement

        # 1. Freshness decay
        current_time = ensure_utc(now)
        created_at = ensure_utc(spree.created_at) if spree.created_at is not None else current_time

        age_seconds = max(0.0, (current_time - created_at).total_seconds())
        age_hours = age_seconds / 3600.0
        freshness_decay = 1.0 / (1.0 + (age_hours / self.half_life_hours))

        # 2. Engagement score
        engagement_score = max(
            0.0,
            (eng.claps_count * self.weight_clap)
            + (eng.comments_count * self.weight_comment)
            + (eng.saves_count * self.weight_save)
            + (eng.shares_count * self.weight_share),
        )

        # 3. Watch quality score
        completion_ratio = (
            min(1.0, max(0.0, float(eng.completed_views_count) / float(eng.views_count)))
            if eng.views_count > 0
            else 0.0
        )
        watch_quality_score = max(
            0.0,
            (eng.views_count * self.weight_view)
            + (completion_ratio * self.weight_completion),
        )

        # 4. Creator affinity boost
        affinity_score = self.affinity_boost if candidate.is_following_creator else 0.0

        # 5. Topic affinity boost
        if candidate.user_topic_affinities is not None:
            topic_boost = self.compute_topic_affinity_boost(spree, candidate.user_topic_affinities)
        elif candidate.topic_affinity_boost > 0.0:
            topic_boost = float(candidate.topic_affinity_boost)
        else:
            topic_boost = 0.0
        topic_boost = max(0.0, topic_boost)

        # Combine signals
        raw_score = max(
            0.0,
            (self.base_score + engagement_score + watch_quality_score) * freshness_decay
            + affinity_score
            + topic_boost,
        )

        # 6. Buzzer multiplier
        buzzer_mult = max(1.0, float(candidate.buzzer_multiplier)) if candidate.is_buzzer_active else 1.0
        if math.isnan(buzzer_mult) or math.isinf(buzzer_mult):
            buzzer_mult = 1.0
        final_score = round(raw_score * buzzer_mult, 4)
        if math.isnan(final_score) or math.isinf(final_score):
            final_score = round(self.base_score, 4)

        breakdown = {
            "freshness_decay": round(freshness_decay, 4),
            "engagement_score": round(engagement_score, 4),
            "watch_quality_score": round(watch_quality_score, 4),
            "affinity_score": round(affinity_score, 4),
            "topic_affinity_boost": round(topic_boost, 4),
            "raw_score": round(raw_score, 4),
            "buzzer_multiplier": round(buzzer_mult, 4),
            "final_score": final_score,
        }

        return ScoredSpreeItem(
            spree=spree,
            score=final_score,
            engagement=eng,
            is_buzzer_active=candidate.is_buzzer_active,
            buzzer_multiplier=buzzer_mult,
            breakdown=breakdown,
        )


class FeedRankingService:
    """
    Discovery Home Feed Ranking Service.
    Applies visibility rules, aggregates candidate engagement signals,
    and runs the pluggable ranking strategy.
    """

    def __init__(
        self,
        db: Session,
        strategy: Optional[FeedRankingStrategy] = None,
        candidate_limit: Optional[int] = 500,
    ):
        self.db = db
        self.strategy = strategy or HeuristicFeedRankingStrategy()
        self.buzzer_repo = BuzzerRepository(db)
        self.candidate_limit = candidate_limit

    def get_ranked_feed(
        self,
        requesting_user: Optional[User] = None,
        spree_type: Optional[SpreeType] = None,
        skip: int = 0,
        limit: int = 20,
        now: Optional[datetime] = None,
    ) -> List[FeedSpreeResponse]:
        skip = max(0, skip)
        limit = max(1, limit)
        current_time = ensure_utc(now)

        # Inactive requesting users are treated as unauthenticated (excluded from visibility/affinity)
        if requesting_user is not None and not requesting_user.is_active:
            requesting_user = None

        # Visibility rules enforcement:
        # - Creator must be active
        # - PRIVATE sprees are strictly excluded from discovery feed
        # - FOLLOWERS_ONLY sprees only included if requesting user follows creator or is the creator
        # - PUBLIC sprees are included
        query = (
            self.db.query(Spree)
            .join(Spree.creator)
            .options(contains_eager(Spree.creator).joinedload(User.profile))
            .filter(User.is_active.is_(True))
        )

        if spree_type is not None:
            query = query.filter(Spree.type == spree_type)

        if requesting_user is None:
            query = query.filter(Spree.visibility == SpreeVisibility.PUBLIC)
        else:
            follow_subquery = (
                self.db.query(Follow.following_id)
                .filter(Follow.follower_id == requesting_user.id)
                .scalar_subquery()
            )
            query = query.filter(
                or_(
                    Spree.visibility == SpreeVisibility.PUBLIC,
                    and_(
                        Spree.visibility == SpreeVisibility.FOLLOWERS_ONLY,
                        or_(
                            Spree.creator_id == requesting_user.id,
                            Spree.creator_id.in_(follow_subquery),
                        ),
                    ),
                )
            )

        # Candidate window ordering and limit
        query = query.order_by(Spree.created_at.desc(), Spree.id.desc())
        if self.candidate_limit is not None:
            query = query.limit(self.candidate_limit)

        candidates = query.all()
        if not candidates:
            return []

        spree_ids = [s.id for s in candidates]

        # Determine creator follow status for candidates only (chunked to ensure parameter safety)
        followed_creator_ids: Set[str] = set()
        if requesting_user is not None:
            candidate_creator_ids = list({s.creator_id for s in candidates})
            for i in range(0, len(candidate_creator_ids), 500):
                chunk = candidate_creator_ids[i : i + 500]
                follows = (
                    self.db.query(Follow.following_id)
                    .filter(
                        Follow.follower_id == requesting_user.id,
                        Follow.following_id.in_(chunk),
                    )
                    .all()
                )
                followed_creator_ids.update(f[0] for f in follows)

        # Batch-fetch topic affinities for authenticated requesting user
        affinity_map: Dict[str, float] = {}
        if requesting_user is not None:
            user_affinities = (
                self.db.query(UserTopicAffinity.topic, UserTopicAffinity.score)
                .filter(UserTopicAffinity.user_id == requesting_user.id)
                .all()
            )
            affinity_map = {row[0]: float(row[1]) for row in user_affinities}

        # Batch-aggregate engagement statistics
        stats_map = self._batch_aggregate_engagement(spree_ids)

        # Batch-query active Buzzer campaigns
        buzzer_map = self.buzzer_repo.get_active_campaigns_for_sprees(
            spree_ids=spree_ids,
            now=current_time,
        )

        # Assemble candidate signal items
        candidate_items: List[SpreeCandidate] = []
        for spree in candidates:
            stat = stats_map.get(spree.id, SpreeEngagementStats())
            campaign = buzzer_map.get(spree.id)
            is_buzzer_active = campaign is not None
            buzzer_mult = campaign.boost_multiplier if campaign else 1.0
            is_following = spree.creator_id in followed_creator_ids if requesting_user else False

            topic_boost = 0.0
            if requesting_user and affinity_map:
                spree_topics = extract_spree_topics(spree)
                topic_boost = sum(affinity_map.get(t, 0.0) for t in spree_topics)

            candidate_items.append(
                SpreeCandidate(
                    spree=spree,
                    engagement=stat,
                    buzzer_multiplier=buzzer_mult,
                    is_buzzer_active=is_buzzer_active,
                    is_following_creator=is_following,
                    topic_affinity_boost=topic_boost,
                    user_topic_affinities=affinity_map if requesting_user else None,
                )
            )

        # Rank candidates via pluggable strategy
        ranked_items = self.strategy.rank_candidates(candidate_items, now=current_time)

        # Paginate results
        paged_items = ranked_items[skip : skip + limit]

        # Convert to response DTOs
        return [self._to_feed_response(item) for item in paged_items]

    def _batch_aggregate_engagement(
        self,
        spree_ids: List[str],
    ) -> Dict[str, SpreeEngagementStats]:
        if not spree_ids:
            return {}

        result: Dict[str, SpreeEngagementStats] = {sid: SpreeEngagementStats() for sid in spree_ids}

        # Batch in chunks of 500 to guarantee database parameter safety
        for i in range(0, len(spree_ids), 500):
            chunk = spree_ids[i : i + 500]

            # 1. Views and completion counts
            views_data = (
                self.db.query(
                    SpreeView.spree_id,
                    func.count(SpreeView.id).label("total_views"),
                    func.sum(case((SpreeView.completed.is_(True), 1), else_=0)).label("completed_views"),
                )
                .filter(SpreeView.spree_id.in_(chunk))
                .group_by(SpreeView.spree_id)
                .all()
            )
            for row in views_data:
                spree_id, total, completed = row[0], row[1] or 0, row[2] or 0
                stats = result[spree_id]
                stats.views_count = int(total)
                stats.completed_views_count = int(completed)
                stats.watch_completion_rate = (
                    round(float(completed) / float(total), 4) if total > 0 else 0.0
                )

            # 2. Claps
            claps_data = (
                self.db.query(SpreeClap.spree_id, func.count(SpreeClap.id))
                .filter(SpreeClap.spree_id.in_(chunk))
                .group_by(SpreeClap.spree_id)
                .all()
            )
            for row in claps_data:
                result[row[0]].claps_count = int(row[1] or 0)

            # 3. Comments
            comments_data = (
                self.db.query(SpreeComment.spree_id, func.count(SpreeComment.id))
                .filter(SpreeComment.spree_id.in_(chunk))
                .group_by(SpreeComment.spree_id)
                .all()
            )
            for row in comments_data:
                result[row[0]].comments_count = int(row[1] or 0)

            # 4. Saves
            saves_data = (
                self.db.query(SpreeSave.spree_id, func.count(SpreeSave.id))
                .filter(SpreeSave.spree_id.in_(chunk))
                .group_by(SpreeSave.spree_id)
                .all()
            )
            for row in saves_data:
                result[row[0]].saves_count = int(row[1] or 0)

            # 5. Shares
            shares_data = (
                self.db.query(SpreeShare.spree_id, func.count(SpreeShare.id))
                .filter(SpreeShare.spree_id.in_(chunk))
                .group_by(SpreeShare.spree_id)
                .all()
            )
            for row in shares_data:
                result[row[0]].shares_count = int(row[1] or 0)

        return result

    def _to_feed_response(self, item: ScoredSpreeItem) -> FeedSpreeResponse:
        spree = item.spree
        eng = item.engagement

        creator_info = None
        if spree.creator:
            profile = getattr(spree.creator, "profile", None)
            creator_info = FeedCreatorInfo(
                id=spree.creator.id,
                username=profile.username if profile else None,
                full_name=profile.full_name if profile else None,
                avatar_url=profile.avatar_url if profile else None,
            )

        metrics = FeedEngagementMetrics(
            views_count=eng.views_count,
            completed_views_count=eng.completed_views_count,
            watch_completion_rate=eng.watch_completion_rate,
            claps_count=eng.claps_count,
            comments_count=eng.comments_count,
            saves_count=eng.saves_count,
            shares_count=eng.shares_count,
        )

        return FeedSpreeResponse(
            id=spree.id,
            creator_id=spree.creator_id,
            type=spree.type,
            title=spree.title,
            description=spree.description,
            media_url=spree.media_url,
            thumbnail_url=spree.thumbnail_url,
            duration=spree.duration,
            visibility=spree.visibility,
            category=spree.category,
            tags=spree.tags if spree.tags is not None else [],
            created_at=spree.created_at,
            updated_at=spree.updated_at,
            creator=creator_info,
            metrics=metrics,
            views_count=eng.views_count,
            claps_count=eng.claps_count,
            comments_count=eng.comments_count,
            saves_count=eng.saves_count,
            shares_count=eng.shares_count,
            score=item.score,
            is_buzzer_active=item.is_buzzer_active,
            boost_multiplier=item.buzzer_multiplier,
        )
