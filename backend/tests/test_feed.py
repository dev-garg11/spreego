from datetime import datetime, timedelta, timezone
import math
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.config.database import Base
from src.config.security import create_access_token
from src.models.buzzer import BuzzerCampaign, BuzzerStatus
from src.models.engagement import (
    SpreeClap,
    SpreeComment,
    SpreeSave,
    SpreeShare,
    SpreeView,
)
from src.models.follow import Follow
from src.models.profile import Profile
from src.models.spree import Spree, SpreeType, SpreeVisibility
from src.models.user import User
from src.services.feed_ranking_service import (
    FeedRankingService,
    FeedRankingStrategy,
    HeuristicFeedRankingStrategy,
    ScoredSpreeItem,
    SpreeCandidate,
    SpreeEngagementStats,
)


# ============================================================================
# Helpers
# ============================================================================

def create_test_user(
    db: Session,
    phone_number: str = None,
    email: str = None,
    username: str = None,
    is_active: bool = True,
) -> User:
    uid = str(uuid.uuid4())[:8]
    phone = phone_number or f"+199{uid[:7]}"
    mail = email or f"user_{uid}@spreego.com"
    handle = username or f"user_{uid}"

    user = User(
        phone_number=phone,
        email=mail,
        is_active=is_active,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    profile = Profile(
        user_id=user.id,
        username=handle,
        full_name=f"Full Name {handle}",
        avatar_url=f"https://cdn.spreego.com/avatars/{handle}.jpg",
    )
    db.add(profile)
    db.commit()
    db.refresh(user)
    return user


def auth_headers(user_id: str) -> dict:
    token = create_access_token(user_id=user_id)
    return {"Authorization": f"Bearer {token}"}


def create_test_spree(
    db: Session,
    creator: User,
    title: str = "Test Spree",
    spree_type: SpreeType = SpreeType.VIDEO_SHORT,
    visibility: SpreeVisibility = SpreeVisibility.PUBLIC,
    created_at: datetime = None,
) -> Spree:
    spree = Spree(
        creator_id=creator.id,
        type=spree_type,
        title=title,
        description=f"Description for {title}",
        media_url="https://cdn.spreego.com/media/test.mp4",
        thumbnail_url="https://cdn.spreego.com/thumbs/test.jpg",
        duration=45.0,
        visibility=visibility,
    )
    if created_at is not None:
        spree.created_at = created_at
    db.add(spree)
    db.commit()
    db.refresh(spree)
    return spree


# ============================================================================
# R1: Database Models & Metadata Verification
# ============================================================================

def test_buzzer_model_registered_in_base_metadata():
    """Verify BuzzerCampaign table is properly registered on Base.metadata."""
    table_names = Base.metadata.tables.keys()
    assert "buzzer_campaigns" in table_names

    table = Base.metadata.tables["buzzer_campaigns"]
    col_names = {c.name for c in table.columns}
    required_cols = {
        "id",
        "spree_id",
        "creator_id",
        "start_at",
        "end_at",
        "status",
        "boost_multiplier",
        "created_at",
    }
    assert required_cols.issubset(col_names)


def test_buzzer_campaign_creation_and_relationships(db_session: Session):
    """Verify BuzzerCampaign model instance creation and ORM relationships."""
    creator = create_test_user(db_session, username="buzzer_creator")
    spree = create_test_spree(db_session, creator=creator, title="Boosted Spree")

    now = datetime.now(timezone.utc)
    campaign = BuzzerCampaign(
        spree_id=spree.id,
        creator_id=creator.id,
        start_at=now,
        end_at=now + timedelta(hours=24),
        status=BuzzerStatus.ACTIVE,
        boost_multiplier=1.8,
    )
    db_session.add(campaign)
    db_session.commit()
    db_session.refresh(campaign)

    assert campaign.id is not None
    assert campaign.spree_id == spree.id
    assert campaign.creator_id == creator.id
    assert campaign.boost_multiplier == 1.8
    assert campaign.status == BuzzerStatus.ACTIVE
    assert campaign.is_active is True
    assert campaign.spree.id == spree.id
    assert campaign.creator.id == creator.id
    assert len(spree.buzzer_campaigns) == 1
    assert len(creator.buzzer_campaigns) == 1


def test_buzzer_campaign_is_active_property():
    """Verify BuzzerCampaign.is_active property handles status and time boundaries."""
    now = datetime.now(timezone.utc)

    # Active within window
    c_active = BuzzerCampaign(
        status=BuzzerStatus.ACTIVE,
        start_at=now - timedelta(hours=1),
        end_at=now + timedelta(hours=23),
    )
    assert c_active.is_active is True

    # Expired by end_at
    c_expired_time = BuzzerCampaign(
        status=BuzzerStatus.ACTIVE,
        start_at=now - timedelta(hours=25),
        end_at=now - timedelta(hours=1),
    )
    assert c_expired_time.is_active is False

    # Inactive status
    c_cancelled = BuzzerCampaign(
        status=BuzzerStatus.CANCELLED,
        start_at=now - timedelta(hours=1),
        end_at=now + timedelta(hours=23),
    )
    assert c_cancelled.is_active is False


# ============================================================================
# R2: Modular Ranking Engine Unit & Integration Tests
# ============================================================================

def test_heuristic_ranking_freshness_decay():
    """Verify that newer content has higher freshness decay score than older content."""
    strategy = HeuristicFeedRankingStrategy()
    now = datetime.now(timezone.utc)

    creator = User(id="u1")
    spree_new = Spree(id="s1", creator_id="u1", created_at=now - timedelta(hours=1))
    spree_old = Spree(id="s2", creator_id="u1", created_at=now - timedelta(hours=48))

    cand_new = SpreeCandidate(spree=spree_new, engagement=strategy.__class__.__name__ and None or None)
    # Using candidate with default zero engagement
    from src.services.feed_ranking_service import SpreeEngagementStats
    cand_new = SpreeCandidate(spree=spree_new, engagement=SpreeEngagementStats())
    cand_old = SpreeCandidate(spree=spree_old, engagement=SpreeEngagementStats())

    scored_new = strategy.score_candidate(cand_new, now)
    scored_old = strategy.score_candidate(cand_old, now)

    assert scored_new.score > scored_old.score
    assert scored_new.breakdown["freshness_decay"] > scored_old.breakdown["freshness_decay"]


def test_heuristic_ranking_engagement_weights():
    """Verify that engagement metrics (claps, comments, saves, shares) increase score."""
    from src.services.feed_ranking_service import SpreeEngagementStats
    strategy = HeuristicFeedRankingStrategy()
    now = datetime.now(timezone.utc)

    spree = Spree(id="s1", creator_id="u1", created_at=now)
    cand_low = SpreeCandidate(spree=spree, engagement=SpreeEngagementStats(claps_count=1))
    cand_high = SpreeCandidate(
        spree=spree,
        engagement=SpreeEngagementStats(
            claps_count=10,
            comments_count=5,
            saves_count=3,
            shares_count=2,
        ),
    )

    scored_low = strategy.score_candidate(cand_low, now)
    scored_high = strategy.score_candidate(cand_high, now)

    assert scored_high.score > scored_low.score
    assert scored_high.breakdown["engagement_score"] > scored_low.breakdown["engagement_score"]


def test_heuristic_ranking_watch_quality():
    """Verify views and watch completion ratio increase watch quality score."""
    from src.services.feed_ranking_service import SpreeEngagementStats
    strategy = HeuristicFeedRankingStrategy()
    now = datetime.now(timezone.utc)

    spree = Spree(id="s1", creator_id="u1", created_at=now)
    cand_low = SpreeCandidate(
        spree=spree,
        engagement=SpreeEngagementStats(views_count=5, completed_views_count=0),
    )
    cand_high = SpreeCandidate(
        spree=spree,
        engagement=SpreeEngagementStats(views_count=10, completed_views_count=8),
    )

    scored_low = strategy.score_candidate(cand_low, now)
    scored_high = strategy.score_candidate(cand_high, now)

    assert scored_high.score > scored_low.score
    assert scored_high.breakdown["watch_quality_score"] > scored_low.breakdown["watch_quality_score"]


def test_heuristic_ranking_creator_affinity():
    """Verify following a creator applies affinity boost to score."""
    from src.services.feed_ranking_service import SpreeEngagementStats
    strategy = HeuristicFeedRankingStrategy()
    now = datetime.now(timezone.utc)

    spree = Spree(id="s1", creator_id="u1", created_at=now)
    cand_unfollowed = SpreeCandidate(
        spree=spree,
        engagement=SpreeEngagementStats(),
        is_following_creator=False,
    )
    cand_followed = SpreeCandidate(
        spree=spree,
        engagement=SpreeEngagementStats(),
        is_following_creator=True,
    )

    scored_unfollowed = strategy.score_candidate(cand_unfollowed, now)
    scored_followed = strategy.score_candidate(cand_followed, now)

    assert scored_followed.score > scored_unfollowed.score
    assert scored_followed.breakdown["affinity_score"] == strategy.affinity_boost
    assert scored_unfollowed.breakdown["affinity_score"] == 0.0


def test_heuristic_ranking_buzzer_multiplier():
    """Verify active Buzzer campaign applies boost multiplier to the score."""
    from src.services.feed_ranking_service import SpreeEngagementStats
    strategy = HeuristicFeedRankingStrategy()
    now = datetime.now(timezone.utc)

    spree = Spree(id="s1", creator_id="u1", created_at=now)
    cand_normal = SpreeCandidate(
        spree=spree,
        engagement=SpreeEngagementStats(),
        is_buzzer_active=False,
        buzzer_multiplier=1.0,
    )
    cand_boosted = SpreeCandidate(
        spree=spree,
        engagement=SpreeEngagementStats(),
        is_buzzer_active=True,
        buzzer_multiplier=2.0,
    )

    scored_normal = strategy.score_candidate(cand_normal, now)
    scored_boosted = strategy.score_candidate(cand_boosted, now)

    assert scored_boosted.score > scored_normal.score
    assert scored_boosted.score == pytest.approx(scored_normal.score * 2.0, rel=1e-3)


def test_pluggable_ranking_strategy_in_service(db_session: Session):
    """Verify custom ranking strategy can be injected into FeedRankingService."""
    class InverseCustomStrategy(FeedRankingStrategy):
        def score_candidate(self, candidate: SpreeCandidate, now: datetime) -> ScoredSpreeItem:
            # Custom deterministic score based on title length
            score = float(len(candidate.spree.title))
            return ScoredSpreeItem(
                spree=candidate.spree,
                score=score,
                engagement=candidate.engagement,
                is_buzzer_active=False,
                buzzer_multiplier=1.0,
                breakdown={"custom": score},
            )

    creator = create_test_user(db_session, username="plug_creator")
    s_short = create_test_spree(db_session, creator=creator, title="A")
    s_long = create_test_spree(db_session, creator=creator, title="Longer Title Here")

    service = FeedRankingService(db_session, strategy=InverseCustomStrategy())
    feed = service.get_ranked_feed()

    assert len(feed) == 2
    assert feed[0].id == s_long.id
    assert feed[1].id == s_short.id


# ============================================================================
# R3: Home Feed Endpoints (GET /api/v1/sprees/feed)
# ============================================================================

def test_feed_returns_ranked_order_not_just_chronological(client: TestClient, db_session: Session):
    """
    Verify feed returns items sorted by ranking score, not simply chronological ID order.
    An older spree with high engagement should outrank a brand-new spree with 0 engagement.
    """
    creator = create_test_user(db_session, username="ranked_creator")
    viewer = create_test_user(db_session, username="feed_viewer")

    now = datetime.now(timezone.utc)
    # Spree 1: Older, created 2 hours ago
    spree_older = create_test_spree(
        db_session,
        creator=creator,
        title="Popular Older Spree",
        created_at=now - timedelta(hours=2),
    )
    # Spree 2: Brand new, created 1 minute ago, 0 engagement
    spree_newer = create_test_spree(
        db_session,
        creator=creator,
        title="Fresh New Spree",
        created_at=now - timedelta(minutes=1),
    )

    # Add significant engagement to older spree
    for i in range(15):
        clapper = create_test_user(db_session, username=f"clapper_{i}_{uuid.uuid4().hex[:4]}")
        db_session.add(SpreeClap(spree_id=spree_older.id, user_id=clapper.id))
    for i in range(5):
        db_session.add(SpreeComment(spree_id=spree_older.id, user_id=viewer.id, text=f"Great {i}!"))
    for _ in range(8):
        db_session.add(SpreeView(spree_id=spree_older.id, user_id=viewer.id, completed=True))
    db_session.commit()

    resp = client.get("/api/v1/sprees/feed")
    assert resp.status_code == 200
    feed = resp.json()

    assert len(feed) >= 2
    feed_ids = [item["id"] for item in feed]
    # Older high-engagement spree must rank ABOVE fresh zero-engagement spree
    assert feed_ids.index(spree_older.id) < feed_ids.index(spree_newer.id)

    older_item = next(item for item in feed if item["id"] == spree_older.id)
    assert older_item["metrics"]["claps_count"] == 15
    assert older_item["metrics"]["comments_count"] == 5
    assert older_item["metrics"]["views_count"] == 8
    assert older_item["score"] > 0


def test_feed_buzzer_boost_elevates_ranking(client: TestClient, db_session: Session):
    """
    Verify that an active Buzzer campaign elevates a Spree's ranking
    over an otherwise equal or older Spree.
    """
    creator = create_test_user(db_session, username="buzzer_rank_creator")
    now = datetime.now(timezone.utc)

    # Spree A: Older (created 6 hours ago)
    spree_a = create_test_spree(
        db_session,
        creator=creator,
        title="Spree A Boosted",
        created_at=now - timedelta(hours=6),
    )
    # Spree B: Newer (created 1 hour ago)
    spree_b = create_test_spree(
        db_session,
        creator=creator,
        title="Spree B Unboosted",
        created_at=now - timedelta(hours=1),
    )

    # Initially, Spree B (newer) ranks higher than Spree A (older)
    initial_resp = client.get("/api/v1/sprees/feed").json()
    ids_initial = [item["id"] for item in initial_resp]
    assert ids_initial.index(spree_b.id) < ids_initial.index(spree_a.id)

    # Now activate Buzzer boost on Spree A with 2.0x multiplier
    buzzer = BuzzerCampaign(
        spree_id=spree_a.id,
        creator_id=creator.id,
        start_at=now - timedelta(minutes=5),
        end_at=now + timedelta(hours=23, minutes=55),
        status=BuzzerStatus.ACTIVE,
        boost_multiplier=2.0,
    )
    db_session.add(buzzer)
    db_session.commit()

    # After Buzzer activation, Spree A should jump ahead of Spree B
    boosted_resp = client.get("/api/v1/sprees/feed").json()
    ids_boosted = [item["id"] for item in boosted_resp]
    assert ids_boosted.index(spree_a.id) < ids_boosted.index(spree_b.id)

    item_a = next(item for item in boosted_resp if item["id"] == spree_a.id)
    assert item_a["is_buzzer_active"] is True
    assert item_a["boost_multiplier"] == 2.0


def test_feed_creator_affinity_increases_score(client: TestClient, db_session: Session):
    """
    Verify that following a creator increases that creator's content score in the personalized feed.
    """
    creator_followed = create_test_user(db_session, username="creator_followed")
    creator_unfollowed = create_test_user(db_session, username="creator_unfollowed")
    user = create_test_user(db_session, username="affinity_user")

    now = datetime.now(timezone.utc)
    spree_unfollowed = create_test_spree(
        db_session,
        creator=creator_unfollowed,
        title="Unfollowed Creator Spree",
        created_at=now - timedelta(minutes=5),
    )
    spree_followed = create_test_spree(
        db_session,
        creator=creator_followed,
        title="Followed Creator Spree",
        created_at=now - timedelta(hours=2),
    )

    # User follows creator_followed
    follow = Follow(follower_id=user.id, following_id=creator_followed.id)
    db_session.add(follow)
    db_session.commit()

    # Authenticated user request gets personalized ranking
    headers = auth_headers(user.id)
    resp = client.get("/api/v1/sprees/feed", headers=headers)
    assert resp.status_code == 200
    feed = resp.json()

    feed_ids = [item["id"] for item in feed]
    # Followed creator's spree is boosted ahead of the slightly newer unfollowed creator's spree
    assert feed_ids.index(spree_followed.id) < feed_ids.index(spree_unfollowed.id)


def test_feed_visibility_rules_private_and_followers_only(client: TestClient, db_session: Session):
    """
    Verify visibility rules in the feed:
    - PRIVATE sprees are never returned.
    - FOLLOWERS_ONLY sprees are excluded for unauthenticated users.
    - FOLLOWERS_ONLY sprees are excluded for non-following users.
    - FOLLOWERS_ONLY sprees are included for verified followers and the creator.
    """
    creator = create_test_user(db_session, username="vis_creator")
    follower = create_test_user(db_session, username="vis_follower")
    stranger = create_test_user(db_session, username="vis_stranger")

    # Setup follow relationship
    db_session.add(Follow(follower_id=follower.id, following_id=creator.id))
    db_session.commit()

    spree_pub = create_test_spree(db_session, creator=creator, title="Public Spree", visibility=SpreeVisibility.PUBLIC)
    spree_priv = create_test_spree(db_session, creator=creator, title="Private Spree", visibility=SpreeVisibility.PRIVATE)
    spree_fol = create_test_spree(db_session, creator=creator, title="Followers Only Spree", visibility=SpreeVisibility.FOLLOWERS_ONLY)

    # 1. Unauthenticated client
    feed_anon = client.get("/api/v1/sprees/feed").json()
    anon_ids = [s["id"] for s in feed_anon]
    assert spree_pub.id in anon_ids
    assert spree_priv.id not in anon_ids
    assert spree_fol.id not in anon_ids

    # 2. Stranger (authenticated, does not follow creator)
    feed_stranger = client.get("/api/v1/sprees/feed", headers=auth_headers(stranger.id)).json()
    stranger_ids = [s["id"] for s in feed_stranger]
    assert spree_pub.id in stranger_ids
    assert spree_priv.id not in stranger_ids
    assert spree_fol.id not in stranger_ids

    # 3. Follower (authenticated, follows creator)
    feed_follower = client.get("/api/v1/sprees/feed", headers=auth_headers(follower.id)).json()
    follower_ids = [s["id"] for s in feed_follower]
    assert spree_pub.id in follower_ids
    assert spree_fol.id in follower_ids
    assert spree_priv.id not in follower_ids

    # 4. Creator themselves (can see their own followers-only sprees, but private stays out of discovery)
    feed_creator = client.get("/api/v1/sprees/feed", headers=auth_headers(creator.id)).json()
    creator_ids = [s["id"] for s in feed_creator]
    assert spree_pub.id in creator_ids
    assert spree_fol.id in creator_ids
    assert spree_priv.id not in creator_ids


def test_feed_excludes_deactivated_users(client: TestClient, db_session: Session):
    """Verify sprees from deactivated creators are excluded from the feed."""
    creator = create_test_user(db_session, username="deact_feed_creator")
    spree = create_test_spree(db_session, creator=creator, title="Spree Before Deact")

    feed_before = client.get("/api/v1/sprees/feed").json()
    assert any(s["id"] == spree.id for s in feed_before)

    # Deactivate creator
    creator.is_active = False
    db_session.commit()

    feed_after = client.get("/api/v1/sprees/feed").json()
    assert not any(s["id"] == spree.id for s in feed_after)


def test_feed_pagination_and_type_filter(client: TestClient, db_session: Session):
    """Verify feed pagination (limit, skip, page) and content type filtering."""
    creator = create_test_user(db_session, username="page_creator")

    for i in range(5):
        create_test_spree(db_session, creator=creator, title=f"Short {i}", spree_type=SpreeType.VIDEO_SHORT)
    for i in range(3):
        create_test_spree(db_session, creator=creator, title=f"Photo {i}", spree_type=SpreeType.PHOTO)

    # Filter by VIDEO_SHORT
    resp_short = client.get("/api/v1/sprees/feed?type=VIDEO_SHORT")
    assert resp_short.status_code == 200
    shorts = resp_short.json()
    assert len(shorts) == 5
    assert all(s["type"] == "VIDEO_SHORT" for s in shorts)

    # Filter by PHOTO
    resp_photo = client.get("/api/v1/sprees/feed?type=PHOTO")
    assert resp_photo.status_code == 200
    photos = resp_photo.json()
    assert len(photos) == 3
    assert all(s["type"] == "PHOTO" for s in photos)

    # Pagination: limit 2, page 1 and page 2
    p1 = client.get("/api/v1/sprees/feed?limit=2&page=1").json()
    p2 = client.get("/api/v1/sprees/feed?limit=2&page=2").json()
    assert len(p1) == 2
    assert len(p2) == 2
    p1_ids = [s["id"] for s in p1]
    p2_ids = [s["id"] for s in p2]
    assert set(p1_ids).isdisjoint(set(p2_ids))


def test_feed_response_contains_creator_info_and_metrics(client: TestClient, db_session: Session):
    """Verify feed items include creator info (handle, avatar) and engagement metrics."""
    creator = create_test_user(db_session, username="meta_creator")
    spree = create_test_spree(db_session, creator=creator, title="Meta Spree")

    resp = client.get("/api/v1/sprees/feed")
    assert resp.status_code == 200
    items = resp.json()
    item = next(s for s in items if s["id"] == spree.id)

    assert "creator" in item
    assert item["creator"]["id"] == creator.id
    assert item["creator"]["username"] == "meta_creator"
    assert "metrics" in item
    assert "views_count" in item["metrics"]
    assert "claps_count" in item["metrics"]
    assert "score" in item
    assert item["score"] is not None


# ============================================================================
# R3: Buzzer Endpoints (POST & GET /api/v1/sprees/{id}/buzzer)
# ============================================================================

def test_activate_buzzer_success(client: TestClient, db_session: Session):
    """Verify Spree creator can successfully activate a 24-hour Buzzer campaign."""
    creator = create_test_user(db_session, username="buzzer_act_creator")
    spree = create_test_spree(db_session, creator=creator, title="Buzzer Boost Me")
    headers = auth_headers(creator.id)

    before_time = datetime.now(timezone.utc) - timedelta(seconds=2)
    resp = client.post(
        f"/api/v1/sprees/{spree.id}/buzzer",
        headers=headers,
        json={"boost_multiplier": 1.75},
    )
    assert resp.status_code == 201
    data = resp.json()

    assert data["spree_id"] == spree.id
    assert data["creator_id"] == creator.id
    assert data["boost_multiplier"] == 1.75
    assert data["status"] == "ACTIVE"
    assert data["is_active"] is True

    # End time should be ~24 hours from start
    start_dt = datetime.fromisoformat(data["start_at"].replace("Z", "+00:00"))
    end_dt = datetime.fromisoformat(data["end_at"].replace("Z", "+00:00"))
    duration = end_dt - start_dt
    assert duration.total_seconds() == pytest.approx(24 * 3600, abs=10)


def test_activate_buzzer_default_multiplier_without_payload(client: TestClient, db_session: Session):
    """Verify default multiplier 1.5x is applied when no payload is provided."""
    creator = create_test_user(db_session, username="buzzer_def_creator")
    spree = create_test_spree(db_session, creator=creator, title="Default Buzzer Spree")
    headers = auth_headers(creator.id)

    resp = client.post(f"/api/v1/sprees/{spree.id}/buzzer", headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["boost_multiplier"] == 1.5


def test_activate_buzzer_forbidden_for_non_owner(client: TestClient, db_session: Session):
    """Verify non-creator receives HTTP 403 Forbidden when trying to activate Buzzer."""
    creator = create_test_user(db_session, username="real_creator")
    imposter = create_test_user(db_session, username="imposter_user")
    spree = create_test_spree(db_session, creator=creator, title="Ownership Test Spree")

    resp = client.post(
        f"/api/v1/sprees/{spree.id}/buzzer",
        headers=auth_headers(imposter.id),
        json={"boost_multiplier": 2.0},
    )
    assert resp.status_code == 403
    assert "creator" in resp.json()["detail"].lower()


def test_activate_buzzer_unauthenticated_fails(client: TestClient, db_session: Session):
    """Verify unauthenticated request to activate Buzzer returns HTTP 401."""
    creator = create_test_user(db_session, username="anon_creator")
    spree = create_test_spree(db_session, creator=creator, title="Unauth Test Spree")

    resp = client.post(f"/api/v1/sprees/{spree.id}/buzzer")
    assert resp.status_code == 401


def test_activate_buzzer_spree_not_found(client: TestClient, db_session: Session):
    """Verify activating Buzzer on non-existent Spree returns HTTP 404."""
    user = create_test_user(db_session, username="missing_spree_user")
    fake_id = str(uuid.uuid4())

    resp = client.post(
        f"/api/v1/sprees/{fake_id}/buzzer",
        headers=auth_headers(user.id),
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_activate_buzzer_duplicate_active_campaign_fails(client: TestClient, db_session: Session):
    """Verify activating Buzzer when an active campaign already exists returns HTTP 400."""
    creator = create_test_user(db_session, username="dup_buzzer_creator")
    spree = create_test_spree(db_session, creator=creator, title="Dup Buzzer Spree")
    headers = auth_headers(creator.id)

    # First activation
    resp1 = client.post(f"/api/v1/sprees/{spree.id}/buzzer", headers=headers)
    assert resp1.status_code == 201

    # Second activation while first is active
    resp2 = client.post(f"/api/v1/sprees/{spree.id}/buzzer", headers=headers)
    assert resp2.status_code == 400
    assert "already exists" in resp2.json()["detail"].lower()


def test_get_buzzer_status_active_campaign(client: TestClient, db_session: Session):
    """Verify GET /api/v1/sprees/{id}/buzzer returns campaign details for active boost."""
    creator = create_test_user(db_session, username="get_buzzer_creator")
    spree = create_test_spree(db_session, creator=creator, title="Get Buzzer Spree")
    headers = auth_headers(creator.id)

    client.post(
        f"/api/v1/sprees/{spree.id}/buzzer",
        headers=headers,
        json={"boost_multiplier": 1.9},
    )

    resp = client.get(f"/api/v1/sprees/{spree.id}/buzzer")
    assert resp.status_code == 200
    data = resp.json()
    assert data["spree_id"] == spree.id
    assert data["status"] == "ACTIVE"
    assert data["boost_multiplier"] == 1.9
    assert data["is_active"] is True


def test_get_buzzer_status_not_found_when_no_campaign(client: TestClient, db_session: Session):
    """Verify GET /api/v1/sprees/{id}/buzzer returns HTTP 404 when no campaign has been activated."""
    creator = create_test_user(db_session, username="no_buzzer_creator")
    spree = create_test_spree(db_session, creator=creator, title="No Buzzer Spree")

    resp = client.get(f"/api/v1/sprees/{spree.id}/buzzer")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_get_buzzer_status_expired_campaign(client: TestClient, db_session: Session):
    """Verify GET /api/v1/sprees/{id}/buzzer reports EXPIRED status once window passes."""
    creator = create_test_user(db_session, username="expired_creator")
    spree = create_test_spree(db_session, creator=creator, title="Expired Spree")

    now = datetime.now(timezone.utc)
    expired_campaign = BuzzerCampaign(
        spree_id=spree.id,
        creator_id=creator.id,
        start_at=now - timedelta(hours=30),
        end_at=now - timedelta(hours=6),
        status=BuzzerStatus.ACTIVE,
        boost_multiplier=1.5,
    )
    db_session.add(expired_campaign)
    db_session.commit()

    resp = client.get(f"/api/v1/sprees/{spree.id}/buzzer")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "EXPIRED"
    assert data["is_active"] is False


def test_feed_empty_database_returns_empty_list(client: TestClient):
    """Verify feed returns an empty list when no sprees exist."""
    resp = client.get("/api/v1/sprees/feed")
    assert resp.status_code == 200
    assert resp.json() == []


def test_feed_skip_beyond_total_returns_empty_list(client: TestClient, db_session: Session):
    """Verify feed returns empty list when skip offset exceeds available sprees."""
    creator = create_test_user(db_session, username="skip_test_creator")
    create_test_spree(db_session, creator=creator, title="Skip Test Spree")

    resp = client.get("/api/v1/sprees/feed?skip=100")
    assert resp.status_code == 200
    assert resp.json() == []


def test_feed_invalid_type_filter_returns_422(client: TestClient):
    """Verify querying feed with an invalid spree type returns HTTP 422."""
    resp = client.get("/api/v1/sprees/feed?type=INVALID_TYPE")
    assert resp.status_code == 422


def test_feed_zero_engagement_handles_division_by_zero(client: TestClient, db_session: Session):
    """Verify spree with 0 views correctly reports 0.0 watch_completion_rate without ZeroDivisionError."""
    creator = create_test_user(db_session, username="zero_eng_creator")
    spree = create_test_spree(db_session, creator=creator, title="Zero Engagement Spree")

    resp = client.get("/api/v1/sprees/feed")
    assert resp.status_code == 200
    items = resp.json()
    item = next(s for s in items if s["id"] == spree.id)
    assert item["metrics"]["views_count"] == 0
    assert item["metrics"]["watch_completion_rate"] == 0.0


def test_activate_buzzer_invalid_multiplier_bounds(client: TestClient, db_session: Session):
    """Verify activating Buzzer with multiplier < 1.0 or > 5.0 returns validation error (422)."""
    creator = create_test_user(db_session, username="bounds_creator")
    spree = create_test_spree(db_session, creator=creator, title="Bounds Spree")
    headers = auth_headers(creator.id)

    # Multiplier < 1.0
    resp_low = client.post(
        f"/api/v1/sprees/{spree.id}/buzzer",
        headers=headers,
        json={"boost_multiplier": 0.5},
    )
    assert resp_low.status_code == 422

    # Multiplier > 5.0
    resp_high = client.post(
        f"/api/v1/sprees/{spree.id}/buzzer",
        headers=headers,
        json={"boost_multiplier": 8.0},
    )
    assert resp_high.status_code == 422


def test_activate_buzzer_after_previous_campaign_expired_succeeds(client: TestClient, db_session: Session):
    """Verify creator can activate a new Buzzer campaign after a prior campaign has expired."""
    creator = create_test_user(db_session, username="reactivate_creator")
    spree = create_test_spree(db_session, creator=creator, title="Reactivate Spree")
    headers = auth_headers(creator.id)

    # Seed an expired campaign
    now = datetime.now(timezone.utc)
    expired_campaign = BuzzerCampaign(
        spree_id=spree.id,
        creator_id=creator.id,
        start_at=now - timedelta(hours=30),
        end_at=now - timedelta(hours=6),
        status=BuzzerStatus.EXPIRED,
        boost_multiplier=1.5,
    )
    db_session.add(expired_campaign)
    db_session.commit()

    # New activation should succeed since old one is expired
    resp = client.post(
        f"/api/v1/sprees/{spree.id}/buzzer",
        headers=headers,
        json={"boost_multiplier": 2.0},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "ACTIVE"
    assert data["boost_multiplier"] == 2.0
    assert data["id"] != expired_campaign.id


# ============================================================================
# Adversarial & Concurrency Tests (Reviewer Pass 1)
# ============================================================================

def test_buzzer_unique_active_index_prevents_simultaneous_active_campaigns(db_session: Session):
    """
    Adversarial: Verify database-level partial unique index strictly prevents
    two simultaneous ACTIVE campaigns for the same spree, but permits multiple
    historical EXPIRED/CANCELLED campaigns.
    """
    from sqlalchemy.exc import IntegrityError

    creator = create_test_user(db_session, username="uq_idx_creator")
    spree = create_test_spree(db_session, creator=creator, title="UQ Spree")
    now = datetime.now(timezone.utc)

    # 1. First active campaign succeeds
    c1 = BuzzerCampaign(
        spree_id=spree.id,
        creator_id=creator.id,
        start_at=now,
        end_at=now + timedelta(hours=24),
        status=BuzzerStatus.ACTIVE,
        boost_multiplier=1.5,
    )
    db_session.add(c1)
    db_session.commit()

    # 2. An expired campaign on same spree succeeds
    c_expired = BuzzerCampaign(
        spree_id=spree.id,
        creator_id=creator.id,
        start_at=now - timedelta(hours=48),
        end_at=now - timedelta(hours=24),
        status=BuzzerStatus.EXPIRED,
        boost_multiplier=1.5,
    )
    db_session.add(c_expired)
    db_session.commit()

    # 3. Second active campaign for SAME spree MUST fail with IntegrityError at DB level
    c2 = BuzzerCampaign(
        spree_id=spree.id,
        creator_id=creator.id,
        start_at=now,
        end_at=now + timedelta(hours=24),
        status=BuzzerStatus.ACTIVE,
        boost_multiplier=2.0,
    )
    db_session.add(c2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_activate_buzzer_natural_expiration_transitions_old_and_activates_new(client: TestClient, db_session: Session):
    """
    Adversarial: When a campaign's 24 hours have elapsed but its status in DB is
    still ACTIVE (naturally expired), activating a new campaign must automatically
    transition the old campaign to EXPIRED and successfully activate the new one.
    """
    creator = create_test_user(db_session, username="natural_exp_creator")
    spree = create_test_spree(db_session, creator=creator, title="Natural Exp Spree")
    headers = auth_headers(creator.id)
    now = datetime.now(timezone.utc)

    # Seed an ACTIVE campaign whose window has elapsed in real time
    old_campaign = BuzzerCampaign(
        spree_id=spree.id,
        creator_id=creator.id,
        start_at=now - timedelta(hours=26),
        end_at=now - timedelta(hours=2),  # ended 2 hours ago
        status=BuzzerStatus.ACTIVE,       # but status was still ACTIVE in DB
        boost_multiplier=1.5,
    )
    db_session.add(old_campaign)
    db_session.commit()

    # Activating new campaign should succeed without unique constraint violation
    resp = client.post(
        f"/api/v1/sprees/{spree.id}/buzzer",
        headers=headers,
        json={"boost_multiplier": 1.9},
    )
    assert resp.status_code == 201
    new_data = resp.json()
    assert new_data["status"] == "ACTIVE"
    assert new_data["boost_multiplier"] == 1.9
    assert new_data["id"] != old_campaign.id

    # Verify old campaign was transitioned to EXPIRED
    db_session.refresh(old_campaign)
    assert old_campaign.status == BuzzerStatus.EXPIRED


def test_activate_buzzer_concurrency_race_condition_handled(client: TestClient, db_session: Session, monkeypatch):
    """
    Adversarial: Simulate race condition where two simultaneous requests bypass
    the existing-check and race to create. The second one hits DB IntegrityError,
    which must be gracefully caught and mapped to HTTP 400 Bad Request.
    """
    from sqlalchemy.exc import IntegrityError
    from src.repositories.buzzer_repository import BuzzerRepository

    creator = create_test_user(db_session, username="race_creator")
    spree = create_test_spree(db_session, creator=creator, title="Race Spree")
    headers = auth_headers(creator.id)

    # Intercept BuzzerRepository.create to simulate IntegrityError from concurrent commit
    def mock_create_integrity_error(self, entity):
        raise IntegrityError("mock UNIQUE constraint failed", params={}, orig=None)

    monkeypatch.setattr(BuzzerRepository, "create", mock_create_integrity_error)

    resp = client.post(f"/api/v1/sprees/{spree.id}/buzzer", headers=headers)
    assert resp.status_code == 400
    assert "already exists" in resp.json()["detail"].lower()


def test_feed_cursor_pagination_integer(client: TestClient, db_session: Session):
    """Verify cursor pagination with plain integer offset cursor."""
    creator = create_test_user(db_session, username="cursor_int_creator")
    for i in range(6):
        create_test_spree(db_session, creator=creator, title=f"Cursor Item {i}")

    # Fetch first 2
    r1 = client.get("/api/v1/sprees/feed?limit=2").json()
    assert len(r1) == 2

    # Fetch next 2 using cursor=2
    r2 = client.get("/api/v1/sprees/feed?limit=2&cursor=2").json()
    assert len(r2) == 2
    assert r1[0]["id"] != r2[0]["id"]
    assert r1[1]["id"] != r2[1]["id"]


def test_feed_cursor_pagination_base64(client: TestClient, db_session: Session):
    """Verify cursor pagination with base64-encoded offset cursor."""
    import base64

    creator = create_test_user(db_session, username="cursor_b64_creator")
    for i in range(4):
        create_test_spree(db_session, creator=creator, title=f"B64 Item {i}")

    # Cursor for offset 2: base64("2") -> "Mg=="
    cursor_token = base64.b64encode(b"2").decode("utf-8")
    resp = client.get(f"/api/v1/sprees/feed?limit=2&cursor={cursor_token}")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2


def test_feed_cursor_invalid_returns_400(client: TestClient):
    """Verify passing an invalid/malformed cursor returns HTTP 400 Bad Request."""
    resp = client.get("/api/v1/sprees/feed?cursor=not-a-valid-cursor-token!")
    assert resp.status_code == 400
    assert "cursor" in resp.json()["detail"].lower()


def test_feed_cursor_negative_offset_returns_400(client: TestClient):
    """Verify passing a negative offset cursor returns HTTP 400 Bad Request."""
    resp = client.get("/api/v1/sprees/feed?cursor=-10")
    assert resp.status_code == 400


def test_spree_cascade_delete_removes_buzzer_campaign(db_session: Session):
    """Verify deleting a Spree cascade-deletes all associated BuzzerCampaign rows."""
    creator = create_test_user(db_session, username="cascade_spree_creator")
    spree = create_test_spree(db_session, creator=creator, title="Cascade Spree")
    now = datetime.now(timezone.utc)

    campaign = BuzzerCampaign(
        spree_id=spree.id,
        creator_id=creator.id,
        start_at=now,
        end_at=now + timedelta(hours=24),
        status=BuzzerStatus.ACTIVE,
    )
    db_session.add(campaign)
    db_session.commit()
    campaign_id = campaign.id

    # Delete spree
    db_session.delete(spree)
    db_session.commit()

    # Campaign must be deleted
    assert db_session.query(BuzzerCampaign).filter(BuzzerCampaign.id == campaign_id).first() is None


def test_user_cascade_delete_removes_buzzer_campaign(db_session: Session):
    """Verify deleting a User cascade-deletes their BuzzerCampaign rows."""
    creator = create_test_user(db_session, username="cascade_user_creator")
    spree = create_test_spree(db_session, creator=creator, title="Cascade User Spree")
    now = datetime.now(timezone.utc)

    campaign = BuzzerCampaign(
        spree_id=spree.id,
        creator_id=creator.id,
        start_at=now,
        end_at=now + timedelta(hours=24),
        status=BuzzerStatus.ACTIVE,
    )
    db_session.add(campaign)
    db_session.commit()
    campaign_id = campaign.id

    # Delete user
    db_session.delete(creator)
    db_session.commit()

    # Campaign must be deleted
    assert db_session.query(BuzzerCampaign).filter(BuzzerCampaign.id == campaign_id).first() is None


def test_spree_active_buzzer_campaign_property(db_session: Session):
    """Verify Spree.active_buzzer_campaign property correctly resolves active campaign."""
    creator = create_test_user(db_session, username="prop_creator")
    spree = create_test_spree(db_session, creator=creator, title="Prop Spree")
    now = datetime.now(timezone.utc)

    assert spree.active_buzzer_campaign is None

    campaign = BuzzerCampaign(
        spree_id=spree.id,
        creator_id=creator.id,
        start_at=now - timedelta(hours=1),
        end_at=now + timedelta(hours=23),
        status=BuzzerStatus.ACTIVE,
        boost_multiplier=1.8,
    )
    db_session.add(campaign)
    db_session.commit()
    db_session.refresh(spree)

    assert spree.active_buzzer_campaign is not None
    assert spree.active_buzzer_campaign.id == campaign.id
    assert spree.active_buzzer_campaign.boost_multiplier == 1.8


def test_buzzer_service_boundary_validation(db_session: Session):
    """Verify BuzzerService directly rejects multiplier < 1.0 or > 5.0 with ValueError."""
    from src.services.buzzer_service import BuzzerService

    creator = create_test_user(db_session, username="direct_bounds_creator")
    spree = create_test_spree(db_session, creator=creator, title="Direct Bounds Spree")
    service = BuzzerService(db_session)

    with pytest.raises(ValueError, match="between 1.0 and 5.0"):
        service.activate_buzzer(spree.id, creator, boost_multiplier=0.9)

    with pytest.raises(ValueError, match="between 1.0 and 5.0"):
        service.activate_buzzer(spree.id, creator, boost_multiplier=5.1)


def test_ranking_strategy_future_created_at_handled():
    """Verify spree with future created_at doesn't produce negative age or crash."""
    from src.services.feed_ranking_service import (
        HeuristicFeedRankingStrategy,
        SpreeCandidate,
        SpreeEngagementStats,
    )

    strategy = HeuristicFeedRankingStrategy(half_life_hours=0)  # test 0 half life guard
    assert strategy.half_life_hours == 0.1  # guarded against 0

    now = datetime.now(timezone.utc)
    future_spree = Spree(id="fut", creator_id="u", created_at=now + timedelta(hours=5))
    cand = SpreeCandidate(spree=future_spree, engagement=SpreeEngagementStats())

    scored = strategy.score_candidate(cand, now)
    assert scored.score > 0
    assert scored.breakdown["freshness_decay"] == 1.0  # max freshness, age=0


def test_ranking_candidate_window_limit(db_session: Session):
    """Verify FeedRankingService candidate_limit windowing bounds candidate retrieval."""
    creator = create_test_user(db_session, username="window_creator")
    now = datetime.now(timezone.utc)

    for i in range(10):
        create_test_spree(
            db_session,
            creator=creator,
            title=f"Window Item {i}",
            created_at=now - timedelta(hours=i),
        )

    # Window of 3 candidates
    service = FeedRankingService(db_session, candidate_limit=3)
    feed = service.get_ranked_feed(limit=10)
    assert len(feed) == 3


# ============================================================================
# Adversarial & Security Tests (Reviewer Pass 2)
# ============================================================================

def test_get_buzzer_private_spree_unauthorized_and_forbidden(client: TestClient, db_session: Session):
    """
    Adversarial Security: Verify GET /api/v1/sprees/{id}/buzzer on a PRIVATE spree
    strictly enforces authorization:
    - Anonymous client receives HTTP 401 Unauthorized.
    - Authenticated non-owner receives HTTP 403 Forbidden.
    - Spree creator receives HTTP 200 OK.
    """
    creator = create_test_user(db_session, username="priv_buzzer_creator")
    stranger = create_test_user(db_session, username="priv_buzzer_stranger")
    spree = create_test_spree(
        db_session,
        creator=creator,
        title="Private Buzzer Spree",
        visibility=SpreeVisibility.PRIVATE,
    )
    headers_creator = auth_headers(creator.id)
    headers_stranger = auth_headers(stranger.id)

    # Creator activates buzzer on private spree
    act_resp = client.post(
        f"/api/v1/sprees/{spree.id}/buzzer",
        headers=headers_creator,
        json={"boost_multiplier": 1.7},
    )
    assert act_resp.status_code == 201

    # 1. Anonymous request MUST be rejected with 401
    resp_anon = client.get(f"/api/v1/sprees/{spree.id}/buzzer")
    assert resp_anon.status_code == 401
    assert "authentication required" in resp_anon.json()["detail"].lower()

    # 2. Stranger request MUST be rejected with 403
    resp_stranger = client.get(f"/api/v1/sprees/{spree.id}/buzzer", headers=headers_stranger)
    assert resp_stranger.status_code == 403
    assert "permission" in resp_stranger.json()["detail"].lower()

    # 3. Creator request MUST succeed with 200
    resp_creator = client.get(f"/api/v1/sprees/{spree.id}/buzzer", headers=headers_creator)
    assert resp_creator.status_code == 200
    data = resp_creator.json()
    assert data["spree_id"] == spree.id
    assert data["boost_multiplier"] == 1.7


def test_get_buzzer_followers_only_spree_visibility_checks(client: TestClient, db_session: Session):
    """
    Adversarial Security: Verify GET /api/v1/sprees/{id}/buzzer on FOLLOWERS_ONLY spree:
    - Anonymous receives HTTP 401.
    - Non-follower receives HTTP 403.
    - Follower receives HTTP 200.
    - Creator receives HTTP 200.
    """
    creator = create_test_user(db_session, username="fol_buzzer_creator")
    follower = create_test_user(db_session, username="fol_buzzer_follower")
    stranger = create_test_user(db_session, username="fol_buzzer_stranger")

    # Follower follows creator
    db_session.add(Follow(follower_id=follower.id, following_id=creator.id))
    db_session.commit()

    spree = create_test_spree(
        db_session,
        creator=creator,
        title="Followers Buzzer Spree",
        visibility=SpreeVisibility.FOLLOWERS_ONLY,
    )

    client.post(
        f"/api/v1/sprees/{spree.id}/buzzer",
        headers=auth_headers(creator.id),
        json={"boost_multiplier": 1.6},
    )

    # 1. Anonymous -> 401
    assert client.get(f"/api/v1/sprees/{spree.id}/buzzer").status_code == 401

    # 2. Stranger -> 403
    resp_stranger = client.get(f"/api/v1/sprees/{spree.id}/buzzer", headers=auth_headers(stranger.id))
    assert resp_stranger.status_code == 403
    assert "follow" in resp_stranger.json()["detail"].lower()

    # 3. Follower -> 200
    resp_follower = client.get(f"/api/v1/sprees/{spree.id}/buzzer", headers=auth_headers(follower.id))
    assert resp_follower.status_code == 200
    assert resp_follower.json()["spree_id"] == spree.id

    # 4. Creator -> 200
    resp_creator = client.get(f"/api/v1/sprees/{spree.id}/buzzer", headers=auth_headers(creator.id))
    assert resp_creator.status_code == 200
    assert resp_creator.json()["spree_id"] == spree.id


def test_buzzer_endpoints_deactivated_creator_returns_404(client: TestClient, db_session: Session):
    """
    Adversarial: When a spree's creator is deactivated, buzzer endpoints
    must treat the spree as not found (HTTP 404).
    """
    creator = create_test_user(db_session, username="deact_buzzer_creator")
    spree = create_test_spree(db_session, creator=creator, title="Deact Creator Spree")
    headers = auth_headers(creator.id)

    # Activate buzzer while active
    resp_act = client.post(f"/api/v1/sprees/{spree.id}/buzzer", headers=headers)
    assert resp_act.status_code == 201

    # Deactivate creator
    creator.is_active = False
    db_session.commit()

    # GET buzzer must return 404
    resp_get = client.get(f"/api/v1/sprees/{spree.id}/buzzer")
    assert resp_get.status_code == 404

    # Direct service call to activate on deactivated creator's spree returns LookupError (404)
    from src.services.buzzer_service import BuzzerService
    service = BuzzerService(db_session)
    with pytest.raises(LookupError, match="Spree not found"):
        service.get_buzzer(spree.id)


def test_activate_buzzer_nan_inf_multiplier_rejected(client: TestClient, db_session: Session):
    """
    Adversarial: Verify NaN and Infinity values for boost_multiplier are rejected
    and cannot bypass boundary checks.
    """
    import math
    from src.services.buzzer_service import BuzzerService

    creator = create_test_user(db_session, username="nan_creator")
    spree = create_test_spree(db_session, creator=creator, title="NaN Spree")
    service = BuzzerService(db_session)

    # Direct service validation catches NaN and Inf
    with pytest.raises(ValueError, match="between 1.0 and 5.0"):
        service.activate_buzzer(spree.id, creator, boost_multiplier=float("nan"))

    with pytest.raises(ValueError, match="between 1.0 and 5.0"):
        service.activate_buzzer(spree.id, creator, boost_multiplier=float("inf"))

    with pytest.raises(ValueError, match="between 1.0 and 5.0"):
        service.activate_buzzer(spree.id, creator, boost_multiplier=float("-inf"))


def test_feed_cursor_unpadded_base64(client: TestClient, db_session: Session):
    """
    Adversarial: Verify feed cursor pagination accepts unpadded URL-safe base64 tokens
    (e.g. 'Mg' without trailing '=').
    """
    import base64
    creator = create_test_user(db_session, username="unpad_creator")
    for i in range(5):
        create_test_spree(db_session, creator=creator, title=f"Unpad Item {i}")

    # base64("2") without padding '=' -> "Mg"
    unpadded_cursor = base64.urlsafe_b64encode(b"2").decode("utf-8").rstrip("=")
    assert not unpadded_cursor.endswith("=")

    resp = client.get(f"/api/v1/sprees/feed?limit=2&cursor={unpadded_cursor}")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2


def test_feed_cursor_empty_string_returns_first_page(client: TestClient, db_session: Session):
    """
    Adversarial: Verify passing an empty or whitespace cursor returns the first page (200)
    rather than a 400 error.
    """
    creator = create_test_user(db_session, username="empty_cursor_creator")
    create_test_spree(db_session, creator=creator, title="Empty Cursor Item")

    resp_empty = client.get("/api/v1/sprees/feed?cursor=")
    assert resp_empty.status_code == 200
    assert len(resp_empty.json()) >= 1

    resp_spaces = client.get("/api/v1/sprees/feed?cursor=%20%20")
    assert resp_spaces.status_code == 200
    assert len(resp_spaces.json()) >= 1


def test_buzzer_campaign_is_active_uncommitted_instance():
    """
    Adversarial: Verify instantiating BuzzerCampaign in memory without start_at/end_at
    does not raise AttributeError when evaluating is_active.
    """
    c = BuzzerCampaign(status=BuzzerStatus.ACTIVE)
    assert c.start_at is None
    assert c.end_at is None
    assert c.is_active is False


def test_cancel_buzzer_campaign_drops_feed_multiplier(client: TestClient, db_session: Session):
    """
    Lifecycle: Verify cancelling an active Buzzer campaign updates status to CANCELLED
    and drops the feed ranking boost multiplier back to 1.0.
    """
    from src.services.buzzer_service import BuzzerService

    creator = create_test_user(db_session, username="cancel_creator")
    spree = create_test_spree(db_session, creator=creator, title="Cancel Buzzer Spree")
    headers = auth_headers(creator.id)

    # 1. Activate buzzer with 2.0x boost
    resp_act = client.post(
        f"/api/v1/sprees/{spree.id}/buzzer",
        headers=headers,
        json={"boost_multiplier": 2.0},
    )
    assert resp_act.status_code == 201

    # 2. Check feed shows active buzzer
    feed_active = client.get("/api/v1/sprees/feed").json()
    item_active = next(s for s in feed_active if s["id"] == spree.id)
    assert item_active["is_buzzer_active"] is True
    assert item_active["boost_multiplier"] == 2.0

    # 3. Cancel buzzer
    service = BuzzerService(db_session)
    cancelled = service.cancel_buzzer(spree.id, creator)
    assert cancelled.status == BuzzerStatus.CANCELLED

    # 4. Check feed shows buzzer is no longer active and multiplier is reset to 1.0
    feed_after = client.get("/api/v1/sprees/feed").json()
    item_after = next(s for s in feed_after if s["id"] == spree.id)
    assert item_after["is_buzzer_active"] is False
    assert item_after["boost_multiplier"] == 1.0

    # 5. GET buzzer shows status CANCELLED and is_active False
    resp_get = client.get(f"/api/v1/sprees/{spree.id}/buzzer", headers=headers)
    assert resp_get.status_code == 200
    assert resp_get.json()["status"] == "CANCELLED"
    assert resp_get.json()["is_active"] is False


def test_ranking_strategy_nan_inf_scores_clamped():
    """
    Adversarial: Verify ranking strategy defends against NaN or Inf values
    in engagement or buzzer multipliers.
    """
    from src.services.feed_ranking_service import (
        HeuristicFeedRankingStrategy,
        SpreeCandidate,
        SpreeEngagementStats,
    )

    strategy = HeuristicFeedRankingStrategy()
    now = datetime.now(timezone.utc)
    spree = Spree(id="nan_spree", creator_id="u", created_at=now)

    cand = SpreeCandidate(
        spree=spree,
        engagement=SpreeEngagementStats(),
        is_buzzer_active=True,
        buzzer_multiplier=float("nan"),
    )

    scored = strategy.score_candidate(cand, now)
    assert not (math.isnan(scored.score) or math.isinf(scored.score))
    assert scored.score > 0
    assert scored.buzzer_multiplier == 1.0


def test_batch_aggregate_large_candidate_chunking(db_session: Session):
    """
    Adversarial Scalability: Verify _batch_aggregate_engagement properly chunks
    candidate queries without exceeding database parameter limits.
    """
    service = FeedRankingService(db_session)
    fake_spree_ids = [f"fake_spree_id_{i}" for i in range(1200)]
    stats = service._batch_aggregate_engagement(fake_spree_ids)
    assert len(stats) == 1200
    assert stats["fake_spree_id_0"].views_count == 0


# ============================================================================
# Adversarial & Edge Case Tests (Reviewer Pass 3)
# ============================================================================

def test_feed_deactivated_requesting_user_treated_as_anonymous(db_session: Session):
    """
    Adversarial: Verify that a deactivated requesting user passed to FeedRankingService
    is treated as unauthenticated (excluded from viewing FOLLOWERS_ONLY content and
    excluded from creator affinity boosts).
    """
    creator = create_test_user(db_session, username="deact_req_creator")
    deact_viewer = create_test_user(db_session, username="deact_viewer", is_active=False)

    # Viewer follows creator
    db_session.add(Follow(follower_id=deact_viewer.id, following_id=creator.id))
    db_session.commit()

    spree_pub = create_test_spree(db_session, creator=creator, title="Pub Spree", visibility=SpreeVisibility.PUBLIC)
    spree_fol = create_test_spree(db_session, creator=creator, title="Fol Spree", visibility=SpreeVisibility.FOLLOWERS_ONLY)

    service = FeedRankingService(db_session)
    feed = service.get_ranked_feed(requesting_user=deact_viewer)
    feed_ids = [s.id for s in feed]

    # Deactivated viewer must NOT see followers-only spree
    assert spree_pub.id in feed_ids
    assert spree_fol.id not in feed_ids

    # Spree should not have affinity boost
    pub_item = next(s for s in feed if s.id == spree_pub.id)
    # Compare with anonymous feed score: must match exactly
    anon_feed = service.get_ranked_feed(requesting_user=None)
    anon_item = next(s for s in anon_feed if s.id == spree_pub.id)
    assert pub_item.score == anon_item.score


def test_get_buzzer_deactivated_requesting_user_rejected(db_session: Session):
    """
    Adversarial: Verify BuzzerService.get_buzzer rejects a deactivated requesting user
    with PermissionError.
    """
    from src.services.buzzer_service import BuzzerService

    creator = create_test_user(db_session, username="buzzer_chk_creator")
    deact_user = create_test_user(db_session, username="buzzer_deact_user", is_active=False)
    spree = create_test_spree(db_session, creator=creator, title="Buzzer Chk Spree")

    service = BuzzerService(db_session)
    with pytest.raises(PermissionError, match="deactivated"):
        service.get_buzzer(spree.id, requesting_user=deact_user)


def test_cancel_buzzer_deactivated_creator_rejected(db_session: Session):
    """
    Adversarial: Verify BuzzerService.cancel_buzzer rejects a deactivated creator
    with PermissionError.
    """
    from src.services.buzzer_service import BuzzerService

    creator = create_test_user(db_session, username="cancel_chk_creator")
    spree = create_test_spree(db_session, creator=creator, title="Cancel Chk Spree")

    service = BuzzerService(db_session)
    service.activate_buzzer(spree.id, creator)

    # Deactivate creator
    creator.is_active = False
    db_session.commit()

    with pytest.raises(PermissionError, match="deactivated"):
        service.cancel_buzzer(spree.id, creator)


def test_feed_cursor_excessive_offset_returns_400(client: TestClient):
    """
    Security/DOS: Verify supplying an excessively large cursor offset (> 100,000)
    returns HTTP 400 Bad Request rather than integer overflow or database crash.
    """
    resp_large_int = client.get("/api/v1/sprees/feed?cursor=99999999999999999999999999999999999999999999999999")
    assert resp_large_int.status_code == 400
    assert "cursor" in resp_large_int.json()["detail"].lower()

    # Also test base64-encoded large offset
    import base64
    large_b64 = base64.urlsafe_b64encode(b"200000").decode("utf-8")
    resp_large_b64 = client.get(f"/api/v1/sprees/feed?cursor={large_b64}")
    assert resp_large_b64.status_code == 400


def test_feed_skip_and_page_excessive_bounds_returns_422(client: TestClient):
    """
    Security/DOS: Verify skip > 100,000 and page > 10,000 return HTTP 422 Unprocessable Entity.
    """
    resp_skip = client.get("/api/v1/sprees/feed?skip=100001")
    assert resp_skip.status_code == 422

    resp_page = client.get("/api/v1/sprees/feed?page=10001")
    assert resp_page.status_code == 422


def test_feed_negative_skip_normalized_safely(db_session: Session):
    """
    Robustness: Verify calling FeedRankingService.get_ranked_feed directly with negative skip
    safely normalizes to 0 without end-of-list slicing anomalies.
    """
    creator = create_test_user(db_session, username="neg_skip_creator")
    s1 = create_test_spree(db_session, creator=creator, title="Neg Item 1")
    s2 = create_test_spree(db_session, creator=creator, title="Neg Item 2")

    service = FeedRankingService(db_session)
    feed_neg = service.get_ranked_feed(skip=-10, limit=2)
    feed_zero = service.get_ranked_feed(skip=0, limit=2)

    assert [s.id for s in feed_neg] == [s.id for s in feed_zero]


def test_ranking_sort_key_none_spree_id_safe():
    """
    Robustness: Verify rank_candidates handles Spree instances with id=None without
    raising TypeError when sorting ties.
    """
    now = datetime.now(timezone.utc)
    s1 = Spree(id=None, creator_id="u", created_at=now)
    s2 = Spree(id=None, creator_id="u", created_at=now)

    strategy = HeuristicFeedRankingStrategy()
    c1 = SpreeCandidate(spree=s1, engagement=SpreeEngagementStats())
    c2 = SpreeCandidate(spree=s2, engagement=SpreeEngagementStats())

    ranked = strategy.rank_candidates([c1, c2], now=now)
    assert len(ranked) == 2


def test_postgres_partial_unique_index_enforcement():
    """
    Integration: Verify the partial unique index uq_buzzer_campaign_active_spree
    on the physical PostgreSQL database if connected to a PostgreSQL instance.
    """
    import os
    from sqlalchemy import create_engine
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm import sessionmaker

    pg_url = os.environ.get("POSTGRES_TEST_DATABASE_URL") or "postgresql://postgres:postgres@localhost:5433/spreego_db"
    try:
        pg_engine = create_engine(pg_url)
        with pg_engine.connect() as conn:
            pass
        Base.metadata.create_all(bind=pg_engine)
    except Exception:
        pytest.skip("Not connected to a live PostgreSQL database")

    Session = sessionmaker(bind=pg_engine)
    db = Session()
    try:
        uid = str(uuid.uuid4())[:8]
        u = User(phone_number=f"+198{uid[:7]}", email=f"pg_u_{uid}@spreego.com")
        db.add(u)
        db.commit()

        s = Spree(creator_id=u.id, type=SpreeType.VIDEO_SHORT, title="PG Live Spree", media_url="http://test")
        db.add(s)
        db.commit()

        now = datetime.now(timezone.utc)
        c1 = BuzzerCampaign(
            spree_id=s.id,
            creator_id=u.id,
            start_at=now,
            end_at=now + timedelta(hours=24),
            status=BuzzerStatus.ACTIVE,
        )
        db.add(c1)
        db.commit()

        c2 = BuzzerCampaign(
            spree_id=s.id,
            creator_id=u.id,
            start_at=now,
            end_at=now + timedelta(hours=24),
            status=BuzzerStatus.ACTIVE,
        )
        db.add(c2)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        # Cleanup
        db.delete(u)
        db.commit()
    finally:
        db.close()



