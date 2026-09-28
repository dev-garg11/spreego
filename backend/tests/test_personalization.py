from datetime import datetime, timedelta, timezone
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from src.config.database import Base
from src.config.security import create_access_token
from src.models.affinity import UserTopicAffinity
from src.models.profile import Profile
from src.models.spree import Spree, SpreeType, SpreeVisibility
from src.models.user import User
from src.services.affinity_service import AffinityService, extract_spree_topics, normalize_topic
from src.services.feed_ranking_service import (
    FeedRankingService,
    HeuristicFeedRankingStrategy,
    ScoredSpreeItem,
    SpreeCandidate,
    SpreeEngagementStats,
)


# ============================================================================
# Test Helpers
# ============================================================================

def create_test_user(
    db: Session,
    username: str = None,
    email: str = None,
    is_active: bool = True,
) -> User:
    """Helper to provision a user and profile directly in test DB."""
    uid = str(uuid.uuid4())[:8]
    handle = username or f"user_{uid}"
    mail = email or f"{handle}@spreego.com"

    user = User(
        phone_number=f"+177{uid[:7]}",
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
        full_name=f"Test {handle}",
        avatar_url="https://cdn.spreego.com/avatars/default.png",
    )
    db.add(profile)
    db.commit()
    db.refresh(user)
    return user


def auth_headers(user_id: str) -> dict:
    """Helper to generate JWT bearer header for user_id."""
    token = create_access_token(user_id=user_id)
    return {"Authorization": f"Bearer {token}"}


def create_test_spree(
    db: Session,
    creator: User,
    title: str = "Test Reel",
    category: str = None,
    tags: list = None,
    duration: float = 30.0,
    created_at: datetime = None,
    visibility: SpreeVisibility = SpreeVisibility.PUBLIC,
) -> Spree:
    """Helper to insert a Spree with category and tags."""
    spree = Spree(
        creator_id=creator.id,
        type=SpreeType.VIDEO_SHORT,
        title=title,
        media_url="https://cdn.spreego.com/videos/test.mp4",
        thumbnail_url="https://cdn.spreego.com/thumbs/test.jpg",
        duration=duration,
        category=category,
        tags=tags or [],
        visibility=visibility,
        created_at=created_at or datetime.now(timezone.utc),
    )
    db.add(spree)
    db.commit()
    db.refresh(spree)
    return spree


# ============================================================================
# R1 Tests: Model & Schemas
# ============================================================================

def test_models_and_metadata_registration():
    """Verify UserTopicAffinity and updated Spree model are registered on Base metadata."""
    table_names = Base.metadata.tables.keys()
    assert "user_topic_affinities" in table_names
    assert "sprees" in table_names

    affinity_table = Base.metadata.tables["user_topic_affinities"]
    col_names = [c.name for c in affinity_table.columns]
    assert "id" in col_names
    assert "user_id" in col_names
    assert "topic" in col_names
    assert "score" in col_names
    assert "updated_at" in col_names

    spree_table = Base.metadata.tables["sprees"]
    spree_cols = [c.name for c in spree_table.columns]
    assert "category" in spree_cols
    assert "tags" in spree_cols


def test_unique_constraint_user_topic_affinity(db_session: Session):
    """Verify unique constraint on (user_id, topic) prevents duplicates."""
    user = create_test_user(db_session, username="uniq_aff_user")
    aff1 = UserTopicAffinity(user_id=user.id, topic="gaming", score=1.0)
    db_session.add(aff1)
    db_session.commit()

    aff2 = UserTopicAffinity(user_id=user.id, topic="gaming", score=2.0)
    db_session.add(aff2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_spree_create_with_category_and_tags_api(client: TestClient, db_session: Session):
    """Verify Spree creation API persists normalized category and tags."""
    user = create_test_user(db_session, username="creator_cat_tags")
    headers = auth_headers(user.id)

    payload = {
        "type": "VIDEO_SHORT",
        "title": "Funny Dog Tricks",
        "media_url": "https://cdn.spreego.com/videos/dog.mp4",
        "category": "Comedy",
        "tags": ["Dogs", "Viral", "pets", "DOGS"],  # Tests normalization & deduplication
        "duration": 15.0,
    }

    resp = client.post("/api/v1/sprees", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["category"] == "comedy"
    assert data["tags"] == ["dogs", "viral", "pets"]

    # Verify directly from DB
    spree = db_session.query(Spree).filter(Spree.id == data["id"]).first()
    assert spree is not None
    assert spree.category == "comedy"
    assert spree.tags == ["dogs", "viral", "pets"]


def test_spree_create_defaults_category_and_tags(client: TestClient, db_session: Session):
    """Verify Spree creation without category/tags defaults to None and empty list."""
    user = create_test_user(db_session, username="creator_defaults")
    headers = auth_headers(user.id)

    payload = {
        "type": "VIDEO_SHORT",
        "title": "Minimal Reel",
        "media_url": "https://cdn.spreego.com/videos/min.mp4",
    }

    resp = client.post("/api/v1/sprees", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["category"] is None
    assert data["tags"] == []


def test_spree_update_category_and_tags_api(client: TestClient, db_session: Session):
    """Verify Spree update endpoint allows updating category and tags via both PUT and PATCH."""
    user = create_test_user(db_session, username="creator_upd")
    spree = create_test_spree(db_session, creator=user, title="Original", category="food", tags=["recipe"])
    headers = auth_headers(user.id)

    # 1. Update via PUT
    update_payload = {
        "category": "Fitness",
        "tags": ["Gym", "Workout"],
    }
    resp = client.put(f"/api/v1/sprees/{spree.id}", json=update_payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["category"] == "fitness"
    assert data["tags"] == ["gym", "workout"]

    # 2. Update via PATCH
    patch_payload = {
        "category": "Tech",
        "tags": ["Coding", "AI"],
    }
    resp_patch = client.patch(f"/api/v1/sprees/{spree.id}", json=patch_payload, headers=headers)
    assert resp_patch.status_code == 200
    data_patch = resp_patch.json()
    assert data_patch["category"] == "tech"
    assert data_patch["tags"] == ["coding", "ai"]


def test_spree_update_tags_null_resets_safely(client: TestClient, db_session: Session):
    """Verify Spree update endpoint gracefully resets tags to empty list when None or [] passed via PUT and PATCH."""
    user = create_test_user(db_session, username="creator_upd_null")
    spree = create_test_spree(db_session, creator=user, title="Has Tags", category="food", tags=["recipe", "pasta"])
    headers = auth_headers(user.id)

    # Update with tags = None via PUT
    resp = client.put(f"/api/v1/sprees/{spree.id}", json={"tags": None}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["tags"] == []

    # Verify directly in DB
    db_session.refresh(spree)
    assert spree.tags == []

    # Re-add tags directly
    spree.tags = ["cooking"]
    db_session.commit()

    # Update with tags = None via PATCH
    resp_patch = client.patch(f"/api/v1/sprees/{spree.id}", json={"tags": None}, headers=headers)
    assert resp_patch.status_code == 200
    assert resp_patch.json()["tags"] == []
    db_session.refresh(spree)
    assert spree.tags == []


# ============================================================================
# R2 Tests: Live Affinity Signal Processing
# ============================================================================

def test_watch_high_completion_increments_affinity(client: TestClient, db_session: Session):
    """
    POST /api/v1/sprees/{id}/view:
    Watching >= 80% or completed == True increments topic affinity by +2.0 points.
    """
    creator = create_test_user(db_session, username="watch_creator")
    viewer = create_test_user(db_session, username="watch_viewer")
    spree = create_test_spree(
        db_session,
        creator=creator,
        title="Workout Routine",
        category="fitness",
        tags=["calisthenics"],
        duration=20.0,
    )
    headers = auth_headers(viewer.id)

    # 1. Watch with 17.0s (17/20 = 85% >= 80%), completed=False
    resp = client.post(
        f"/api/v1/sprees/{spree.id}/view",
        json={"watch_duration": 17.0, "completed": False},
        headers=headers,
    )
    assert resp.status_code == 200

    aff_service = AffinityService(db_session)
    affinities = aff_service.get_user_affinities(viewer.id)
    assert affinities.get("fitness") == 2.0
    assert affinities.get("calisthenics") == 2.0

    # 2. Watch again with completed=True
    resp2 = client.post(
        f"/api/v1/sprees/{spree.id}/view",
        json={"watch_duration": 20.0, "completed": True},
        headers=headers,
    )
    assert resp2.status_code == 200

    affinities2 = aff_service.get_user_affinities(viewer.id)
    assert affinities2.get("fitness") == 4.0
    assert affinities2.get("calisthenics") == 4.0


def test_watch_skip_decrements_affinity_with_floor_zero(client: TestClient, db_session: Session):
    """
    POST /api/v1/sprees/{id}/view:
    Skipping video (< 3.0 seconds) decrements topic affinity by -1.0 point, floored at 0.0.
    """
    creator = create_test_user(db_session, username="skip_creator")
    viewer = create_test_user(db_session, username="skip_viewer")
    spree = create_test_spree(
        db_session,
        creator=creator,
        title="Boring Gaming Clip",
        category="gaming",
        tags=["speedrun"],
        duration=60.0,
    )
    headers = auth_headers(viewer.id)
    aff_service = AffinityService(db_session)

    # Pre-populate affinity: gaming = 1.5, speedrun = 0.5
    aff_service.update_topic_score(viewer.id, "gaming", 1.5)
    aff_service.update_topic_score(viewer.id, "speedrun", 0.5)

    # User skips at 1.8 seconds (< 3.0s, completed=False)
    resp = client.post(
        f"/api/v1/sprees/{spree.id}/view",
        json={"watch_duration": 1.8, "completed": False},
        headers=headers,
    )
    assert resp.status_code == 200

    affinities = aff_service.get_user_affinities(viewer.id)
    assert affinities.get("gaming") == 0.5  # 1.5 - 1.0 = 0.5
    assert affinities.get("speedrun") == 0.0  # 0.5 - 1.0 floored at 0.0

    # Skip again -> gaming decrements from 0.5 to 0.0, speedrun stays 0.0
    client.post(
        f"/api/v1/sprees/{spree.id}/view",
        json={"watch_duration": 0.5, "completed": False},
        headers=headers,
    )
    affinities2 = aff_service.get_user_affinities(viewer.id)
    assert affinities2.get("gaming") == 0.0
    assert affinities2.get("speedrun") == 0.0


def test_watch_intermediate_duration_does_not_modify_affinity(client: TestClient, db_session: Session):
    """
    Watching between 3.0s and <80% of duration (without completed=True) does not increment or decrement.
    """
    creator = create_test_user(db_session, username="inter_creator")
    viewer = create_test_user(db_session, username="inter_viewer")
    spree = create_test_spree(
        db_session,
        creator=creator,
        category="cooking",
        tags=["pasta"],
        duration=30.0,
    )
    headers = auth_headers(viewer.id)
    aff_service = AffinityService(db_session)
    aff_service.update_topic_score(viewer.id, "cooking", 5.0)

    # Watch 10.0 seconds (10/30 = 33.3%, > 3.0s and < 80%)
    resp = client.post(
        f"/api/v1/sprees/{spree.id}/view",
        json={"watch_duration": 10.0, "completed": False},
        headers=headers,
    )
    assert resp.status_code == 200

    affinities = aff_service.get_user_affinities(viewer.id)
    assert affinities.get("cooking") == 5.0
    assert "pasta" not in affinities


def test_clap_save_share_affinity_increments(client: TestClient, db_session: Session):
    """
    Verify Active Engagement Signals:
    - Clap: +1.5 points
    - Save: +3.0 points
    - Share: +5.0 points
    """
    creator = create_test_user(db_session, username="act_creator")
    viewer = create_test_user(db_session, username="act_viewer")
    spree = create_test_spree(
        db_session,
        creator=creator,
        category="dance",
        tags=["hiphop"],
    )
    headers = auth_headers(viewer.id)
    aff_service = AffinityService(db_session)

    # 1. Clap: +1.5
    resp_clap = client.post(f"/api/v1/sprees/{spree.id}/clap", headers=headers)
    assert resp_clap.status_code == 200
    affs = aff_service.get_user_affinities(viewer.id)
    assert affs.get("dance") == 1.5
    assert affs.get("hiphop") == 1.5

    # 2. Save: +3.0 -> total 4.5
    resp_save = client.post(f"/api/v1/sprees/{spree.id}/save", headers=headers)
    assert resp_save.status_code == 200
    affs = aff_service.get_user_affinities(viewer.id)
    assert affs.get("dance") == 4.5
    assert affs.get("hiphop") == 4.5

    # 3. Share: +5.0 -> total 9.5
    resp_share = client.post(f"/api/v1/sprees/{spree.id}/share", json={"platform": "whatsapp"}, headers=headers)
    assert resp_share.status_code == 200
    affs = aff_service.get_user_affinities(viewer.id)
    assert affs.get("dance") == 9.5
    assert affs.get("hiphop") == 9.5


def test_anonymous_view_and_share_safe(client: TestClient, db_session: Session):
    """Verify anonymous view and share operations succeed without error or affinity mutations."""
    creator = create_test_user(db_session, username="anon_creator")
    spree = create_test_spree(db_session, creator=creator, category="travel", tags=["paris"])

    # Anonymous view
    resp_view = client.post(f"/api/v1/sprees/{spree.id}/view", json={"watch_duration": 10.0, "completed": True})
    assert resp_view.status_code == 200

    # Anonymous share
    resp_share = client.post(f"/api/v1/sprees/{spree.id}/share", json={"platform": "twitter"})
    assert resp_share.status_code == 200

    # No affinities created
    count = db_session.query(UserTopicAffinity).count()
    assert count == 0


# ============================================================================
# R3 Tests: Feed Personalization & Ranking Boost
# ============================================================================

def test_feed_personalization_boosts_high_affinity_topic(client: TestClient, db_session: Session):
    """
    Home Feed (GET /api/v1/sprees/feed) demonstrates that a user with high affinity in topic A
    receives topic A videos ranked significantly higher than equal or newer videos from un-engaged topics.
    """
    creator1 = create_test_user(db_session, username="tech_creator")
    creator2 = create_test_user(db_session, username="fashion_creator")
    viewer = create_test_user(db_session, username="tech_enthusiast")

    now = datetime.now(timezone.utc)
    # Spree 1 (Tech): Older, created 4 hours ago, 0 initial engagement
    spree_tech = create_test_spree(
        db_session,
        creator=creator1,
        title="Quantum Computing In Depth",
        category="tech",
        tags=["quantum"],
        created_at=now - timedelta(hours=4),
    )
    # Spree 2 (Fashion): Brand new, created 5 minutes ago, 0 initial engagement
    spree_fashion = create_test_spree(
        db_session,
        creator=creator2,
        title="Summer Outfit Guide",
        category="fashion",
        tags=["style"],
        created_at=now - timedelta(minutes=5),
    )

    # Viewer has built up a high affinity score for "tech"
    aff_service = AffinityService(db_session)
    aff_service.update_topic_score(viewer.id, "tech", 20.0)

    # 1. Unauthenticated feed sees the newer Spree first (freshness wins baseline)
    unauth_resp = client.get("/api/v1/sprees/feed").json()
    unauth_ids = [item["id"] for item in unauth_resp]
    assert unauth_ids.index(spree_fashion.id) < unauth_ids.index(spree_tech.id)

    # 2. Authenticated user feed gets personalized topic affinity boost
    auth_resp = client.get("/api/v1/sprees/feed", headers=auth_headers(viewer.id)).json()
    auth_ids = [item["id"] for item in auth_resp]
    # Spree Tech must rank HIGHER than Spree Fashion for this user!
    assert auth_ids.index(spree_tech.id) < auth_ids.index(spree_fashion.id)

    tech_item = next(item for item in auth_resp if item["id"] == spree_tech.id)
    fashion_item = next(item for item in auth_resp if item["id"] == spree_fashion.id)
    assert tech_item["score"] > fashion_item["score"]
    assert tech_item["category"] == "tech"
    assert "quantum" in tech_item["tags"]


def test_cold_start_ranking_for_new_and_unauthenticated_users(client: TestClient, db_session: Session):
    """
    Verify cold start: new users with 0 affinities and unauthenticated users receive
    normal baseline discovery ranking.
    """
    creator = create_test_user(db_session, username="cold_creator")
    new_user = create_test_user(db_session, username="brand_new_user")

    now = datetime.now(timezone.utc)
    spree_older = create_test_spree(
        db_session,
        creator=creator,
        title="Older Video",
        category="cars",
        created_at=now - timedelta(hours=3),
    )
    spree_newer = create_test_spree(
        db_session,
        creator=creator,
        title="Newer Video",
        category="science",
        created_at=now - timedelta(minutes=10),
    )

    # Both unauthenticated and new user see newer video ahead of older video
    unauth_resp = client.get("/api/v1/sprees/feed").json()
    assert [i["id"] for i in unauth_resp][:2] == [spree_newer.id, spree_older.id]

    auth_resp = client.get("/api/v1/sprees/feed", headers=auth_headers(new_user.id)).json()
    assert [i["id"] for i in auth_resp][:2] == [spree_newer.id, spree_older.id]


def test_anti_fatigue_diversity_prevents_creator_monopoly():
    """
    Anti-fatigue check: ensure diverse ranking so a single creator doesn't
    completely monopolize consecutive feed items.
    """
    strategy = HeuristicFeedRankingStrategy(max_consecutive_creator=2)
    now = datetime.now(timezone.utc)

    # Creator A has 3 high-scoring candidate videos
    # Creator B has 1 medium-scoring video
    sprees_a = [
        Spree(id=f"a_{i}", creator_id="creator_a", created_at=now - timedelta(minutes=i))
        for i in range(3)
    ]
    spree_b = Spree(id="b_1", creator_id="creator_b", created_at=now - timedelta(minutes=10))

    # Give A higher scores than B
    c_a0 = SpreeCandidate(spree=sprees_a[0], engagement=SpreeEngagementStats(claps_count=50))
    c_a1 = SpreeCandidate(spree=sprees_a[1], engagement=SpreeEngagementStats(claps_count=40))
    c_a2 = SpreeCandidate(spree=sprees_a[2], engagement=SpreeEngagementStats(claps_count=30))
    c_b = SpreeCandidate(spree=spree_b, engagement=SpreeEngagementStats(claps_count=10))

    ranked = strategy.rank_candidates([c_a0, c_a1, c_a2, c_b], now=now)
    ranked_creator_ids = [item.spree.creator_id for item in ranked]

    # After 2 items from creator_a, creator_b MUST be interleaved before the 3rd item from creator_a!
    assert ranked_creator_ids == ["creator_a", "creator_a", "creator_b", "creator_a"]


def test_anti_fatigue_single_creator_handles_gracefully():
    """Verify anti-fatigue does not drop items if all candidates belong to one creator."""
    strategy = HeuristicFeedRankingStrategy(max_consecutive_creator=2)
    now = datetime.now(timezone.utc)

    sprees = [
        Spree(id=f"only_a_{i}", creator_id="creator_solo", created_at=now - timedelta(minutes=i))
        for i in range(4)
    ]
    candidates = [
        SpreeCandidate(spree=s, engagement=SpreeEngagementStats(claps_count=10 - idx))
        for idx, s in enumerate(sprees)
    ]

    ranked = strategy.rank_candidates(candidates, now=now)
    assert len(ranked) == 4
    assert [item.spree.id for item in ranked] == ["only_a_0", "only_a_1", "only_a_2", "only_a_3"]


def test_topic_normalization_and_deduplication():
    """Verify helper extract_spree_topics correctly trims, lowercases, and deduplicates."""
    spree = Spree(
        category="  Comedy ",
        tags=["comedy", "JOKES", "  standup  ", "jokes", ""],
    )
    topics = extract_spree_topics(spree)
    assert topics == ["comedy", "jokes", "standup"]


def test_heuristic_feed_ranking_strategy_direct_affinity_computation():
    """Verify HeuristicFeedRankingStrategy computes topic_affinity_boost directly."""
    strategy = HeuristicFeedRankingStrategy()
    now = datetime.now(timezone.utc)

    spree = Spree(id="spree_aff", creator_id="c1", category="tech", tags=["ai", "python"])
    user_affinities = {"tech": 10.0, "ai": 5.0, "gaming": 8.0}

    # Test compute_topic_affinity_boost helper directly
    boost = strategy.compute_topic_affinity_boost(spree, user_affinities)
    assert boost == 15.0  # tech (10) + ai (5)

    # Test candidate scoring with user_topic_affinities
    candidate = SpreeCandidate(
        spree=spree,
        engagement=SpreeEngagementStats(),
        user_topic_affinities=user_affinities,
    )
    scored = strategy.score_candidate(candidate, now)
    assert scored.breakdown["topic_affinity_boost"] == 15.0
    assert scored.score >= 25.0  # base_score (10) + topic_affinity_boost (15)


def test_extract_spree_topics_with_hashtags_and_json_string():
    """Verify topic extraction cleanly handles hashtags, JSON string serialization, and whitespace."""
    spree = Spree(
        category="#Fitness",
        tags='["#Workout", "GYM", "  #fitness  "]',
    )
    topics = extract_spree_topics(spree)
    assert topics == ["fitness", "workout", "gym"]


def test_affinity_service_batch_atomic_update(db_session: Session):
    """Verify AffinityService.update_topics_score batch updates/inserts multiple topics atomically."""
    user = create_test_user(db_session, username="batch_aff_user")
    service = AffinityService(db_session)

    # First batch update (creates records)
    service.update_topics_score(user.id, ["comedy", "dance", "music"], delta=2.5)
    affs = service.get_user_affinities(user.id)
    assert affs == {"comedy": 2.5, "dance": 2.5, "music": 2.5}

    # Second batch update with mixed increment
    service.update_topics_score(user.id, ["comedy", "music"], delta=1.5)
    affs2 = service.get_user_affinities(user.id)
    assert affs2["comedy"] == 4.0
    assert affs2["dance"] == 2.5
    assert affs2["music"] == 4.0


def test_short_video_completed_increments_not_skips(client: TestClient, db_session: Session):
    """
    Edge Case: A short video (duration 2.0s) watched to completion (completed=True)
    must receive the +2.0 boost, NOT the -1.0 early-skip penalty, even though duration < 3.0s.
    """
    creator = create_test_user(db_session, username="short_creator")
    viewer = create_test_user(db_session, username="short_viewer")
    spree = create_test_spree(
        db_session,
        creator=creator,
        title="Micro Clip",
        category="comedy",
        tags=["shortjoke"],
        duration=2.0,
    )
    headers = auth_headers(viewer.id)

    # 1. Watch 2.0s with completed=True -> +2.0 points
    resp = client.post(
        f"/api/v1/sprees/{spree.id}/view",
        json={"watch_duration": 2.0, "completed": True},
        headers=headers,
    )
    assert resp.status_code == 200

    aff_service = AffinityService(db_session)
    affs = aff_service.get_user_affinities(viewer.id)
    assert affs.get("comedy") == 2.0
    assert affs.get("shortjoke") == 2.0

    # 2. Watch 1.8s (1.8/2.0 = 90% >= 80%) with completed=False -> another +2.0 points
    resp2 = client.post(
        f"/api/v1/sprees/{spree.id}/view",
        json={"watch_duration": 1.8, "completed": False},
        headers=headers,
    )
    assert resp2.status_code == 200

    affs2 = aff_service.get_user_affinities(viewer.id)
    assert affs2.get("comedy") == 4.0
    assert affs2.get("shortjoke") == 4.0


def test_tag_length_clamped_to_100_chars(client: TestClient, db_session: Session):
    """
    Edge Case: Verify tags longer than 100 characters are safely clamped to <= 100 characters,
    preventing PostgreSQL DataError (character varying(100)).
    """
    creator = create_test_user(db_session, username="long_tag_creator")
    headers = auth_headers(creator.id)

    long_tag = "x" * 150
    resp = client.post(
        "/api/v1/sprees",
        json={
            "type": "VIDEO_SHORT",
            "title": "Long Tag Reel",
            "media_url": "https://cdn.spreego.com/videos/longtag.mp4",
            "tags": [long_tag],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["tags"][0]) <= 100
    assert data["tags"][0] == "x" * 100

    # User clapping this spree should safely record affinity with <= 100 char topic
    viewer = create_test_user(db_session, username="long_tag_viewer")
    resp_clap = client.post(f"/api/v1/sprees/{data['id']}/clap", headers=auth_headers(viewer.id))
    assert resp_clap.status_code == 200

    aff_service = AffinityService(db_session)
    affs = aff_service.get_user_affinities(viewer.id)
    assert "x" * 100 in affs
    assert affs["x" * 100] == 1.5


def test_strategy_override_topic_affinity_boost():
    """
    Clean Architecture: Verify a subclass overriding compute_topic_affinity_boost
    is respected when scoring candidates with user_topic_affinities.
    """
    class DoubledAffinityStrategy(HeuristicFeedRankingStrategy):
        def compute_topic_affinity_boost(self, spree, user_affinities):
            return super().compute_topic_affinity_boost(spree, user_affinities) * 2.0

    strategy = DoubledAffinityStrategy()
    now = datetime.now(timezone.utc)
    spree = Spree(id="spree_double", creator_id="c_d", category="fitness", tags=["gym"])
    user_affinities = {"fitness": 5.0, "gym": 5.0}

    cand = SpreeCandidate(
        spree=spree,
        engagement=SpreeEngagementStats(),
        user_topic_affinities=user_affinities,
    )
    scored = strategy.score_candidate(cand, now)
    # Base boost is 10.0, doubled is 20.0
    assert scored.breakdown["topic_affinity_boost"] == 20.0
    assert scored.score >= 30.0  # base_score (10) + topic_affinity_boost (20)


def test_process_view_nan_and_inf_safe(db_session: Session):
    """
    Robustness: Verify process_view_signal gracefully ignores NaN and Inf watch_duration.
    """
    user = create_test_user(db_session, username="nan_view_user")
    spree = create_test_spree(db_session, creator=user, category="sports", duration=10.0)
    service = AffinityService(db_session)

    # Pass float("nan")
    service.process_view_signal(user.id, spree, watch_duration=float("nan"), completed=False)
    # Pass float("inf")
    service.process_view_signal(user.id, spree, watch_duration=float("inf"), completed=False)

    # Affinities should not be modified or crashed
    affs = service.get_user_affinities(user.id)
    assert affs == {}


def test_duplicate_clap_and_save_does_not_inflate_affinity(client: TestClient, db_session: Session):
    """
    Robustness / Anti-Gaming: Verify that duplicate idempotent claps and saves
    do not repeatedly boost the user's affinity score on the same spree.
    """
    creator = create_test_user(db_session, username="dup_creator")
    viewer = create_test_user(db_session, username="dup_viewer")
    spree = create_test_spree(
        db_session,
        creator=creator,
        category="art",
        tags=["sketching"],
    )
    headers = auth_headers(viewer.id)
    aff_service = AffinityService(db_session)

    # 1. First clap -> +1.5
    resp1 = client.post(f"/api/v1/sprees/{spree.id}/clap", headers=headers)
    assert resp1.status_code == 200
    affs = aff_service.get_user_affinities(viewer.id)
    assert affs.get("art") == 1.5

    # 2. Duplicate clap -> still 1.5 (NOT 3.0!)
    resp2 = client.post(f"/api/v1/sprees/{spree.id}/clap", headers=headers)
    assert resp2.status_code == 200
    affs2 = aff_service.get_user_affinities(viewer.id)
    assert affs2.get("art") == 1.5

    # 3. First save -> +3.0 (total 4.5)
    resp3 = client.post(f"/api/v1/sprees/{spree.id}/save", headers=headers)
    assert resp3.status_code == 200
    affs3 = aff_service.get_user_affinities(viewer.id)
    assert affs3.get("art") == 4.5

    # 4. Duplicate save -> still 4.5 (NOT 7.5!)
    resp4 = client.post(f"/api/v1/sprees/{spree.id}/save", headers=headers)
    assert resp4.status_code == 200
    affs4 = aff_service.get_user_affinities(viewer.id)
    assert affs4.get("art") == 4.5


def test_photo_spree_view_does_not_skip_decrement(client: TestClient, db_session: Session):
    """
    Edge Case: Viewing a PHOTO spree for < 3s without completion should NOT trigger
    an early-skip penalty decrement (-1.0), as photos are not videos.
    """
    creator = create_test_user(db_session, username="photo_creator")
    viewer = create_test_user(db_session, username="photo_viewer")
    photo_spree = Spree(
        creator_id=creator.id,
        type=SpreeType.PHOTO,
        title="Landscape Photo",
        media_url="https://cdn.spreego.com/photos/landscape.jpg",
        category="photography",
        tags=["nature"],
        visibility=SpreeVisibility.PUBLIC,
    )
    db_session.add(photo_spree)
    db_session.commit()
    db_session.refresh(photo_spree)

    aff_service = AffinityService(db_session)
    aff_service.update_topic_score(viewer.id, "photography", 5.0)

    # View photo for 1.5s with completed=False
    resp = client.post(
        f"/api/v1/sprees/{photo_spree.id}/view",
        json={"watch_duration": 1.5, "completed": False},
        headers=auth_headers(viewer.id),
    )
    assert resp.status_code == 200

    # Score must remain 5.0 (NOT decremented to 4.0!)
    affs = aff_service.get_user_affinities(viewer.id)
    assert affs.get("photography") == 5.0


def test_category_strips_hashtag_and_clamps_length(client: TestClient, db_session: Session):
    """
    Schema Hardening: Verify category automatically strips leading '#' and clamps to 100 chars,
    matching normalize_topic behavior across creation and updates.
    """
    creator = create_test_user(db_session, username="hash_creator")
    headers = auth_headers(creator.id)

    # Create with '#Fitness'
    resp = client.post(
        "/api/v1/sprees",
        json={
            "type": "VIDEO_SHORT",
            "title": "CrossFit Session",
            "media_url": "https://cdn.spreego.com/videos/crossfit.mp4",
            "category": "  #Fitness  ",
            "tags": ["#CrossFit", "WOD"],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["category"] == "fitness"
    assert data["tags"] == ["crossfit", "wod"]

    spree_id = data["id"]

    # Update with '#Technology'
    resp_upd = client.patch(
        f"/api/v1/sprees/{spree_id}",
        json={"category": "#Technology"},
        headers=headers,
    )
    assert resp_upd.status_code == 200
    assert resp_upd.json()["category"] == "technology"


def test_user_topic_affinity_score_non_negative_constraint(db_session: Session):
    """
    Database Integrity: Verify UserTopicAffinity CheckConstraint rejects negative scores at the DB level.
    """
    user = create_test_user(db_session, username="check_user")
    invalid_aff = UserTopicAffinity(user_id=user.id, topic="banned", score=-5.0)
    db_session.add(invalid_aff)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
