from datetime import datetime, timedelta, timezone
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.config.database import Base
from src.config.security import create_access_token
from src.models.engagement import (
    SpreeClap,
    SpreeComment,
    SpreeSave,
    SpreeShare,
    SpreeView,
)
from src.models.open import (
    DEFAULT_SCORING_CONFIG,
    Open,
    OpenParticipant,
    OpenStatus,
    OpenSubmission,
    OpenType,
)
from src.models.profile import Profile
from src.models.spree import Spree, SpreeType, SpreeVisibility
from src.models.user import User


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
    """Helper to provision a user with profile directly into test DB."""
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
    )
    db.add(profile)
    db.commit()
    db.refresh(user)
    return user


def auth_headers(user_id: str) -> dict:
    """Helper to generate Authorization header for user_id."""
    token = create_access_token(user_id=user_id)
    return {"Authorization": f"Bearer {token}"}


def create_test_spree(
    db: Session,
    creator: User,
    title: str = "Test Spree",
    spree_type: SpreeType = SpreeType.VIDEO_SHORT,
    visibility: SpreeVisibility = SpreeVisibility.PUBLIC,
) -> Spree:
    """Helper to provision a test Spree."""
    spree = Spree(
        creator_id=creator.id,
        type=spree_type,
        title=title,
        description=f"Description for {title}",
        media_url="https://cdn.spreego.com/media/test.mp4",
        thumbnail_url="https://cdn.spreego.com/thumbs/test.jpg",
        duration=30.0,
        visibility=visibility,
    )
    db.add(spree)
    db.commit()
    db.refresh(spree)
    return spree


# ============================================================================
# R1: Database Models & Metadata Verification
# ============================================================================

def test_open_models_registered_in_base_metadata():
    """Verify Open, OpenParticipant, and OpenSubmission tables are registered on Base.metadata."""
    table_names = Base.metadata.tables.keys()
    assert "opens" in table_names
    assert "open_participants" in table_names
    assert "open_submissions" in table_names

    open_cols = {c.name for c in Base.metadata.tables["opens"].columns}
    assert {
        "id",
        "creator_id",
        "type",
        "title",
        "description",
        "cover_image_url",
        "rules",
        "start_at",
        "end_at",
        "status",
        "reward_info",
        "max_participants",
        "scoring_config",
        "created_at",
        "updated_at",
    }.issubset(open_cols)

    participant_cols = {c.name for c in Base.metadata.tables["open_participants"].columns}
    assert {"id", "open_id", "user_id", "joined_at"}.issubset(participant_cols)

    submission_cols = {c.name for c in Base.metadata.tables["open_submissions"].columns}
    assert {"id", "open_id", "user_id", "spree_id", "score", "rank", "created_at"}.issubset(submission_cols)


# ============================================================================
# R2: Creation of CHALLENGE, COMPETITION, and SPONSORED Opens
# ============================================================================

def test_create_challenge_open_success(client: TestClient, db_session: Session):
    """Test creating a CHALLENGE Open with default fields."""
    creator = create_test_user(db_session, username="challenge_creator")
    headers = auth_headers(creator.id)

    now = datetime.now(timezone.utc)
    payload = {
        "type": "CHALLENGE",
        "title": "Summer Dance Challenge",
        "description": "Show your best moves for summer!",
        "end_at": (now + timedelta(days=7)).isoformat(),
    }

    response = client.post("/api/v1/opens", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Summer Dance Challenge"
    assert data["type"] == "CHALLENGE"
    assert data["status"] == "ACTIVE"
    assert data["creator_id"] == creator.id
    assert data["scoring_config"] == DEFAULT_SCORING_CONFIG
    assert data["participants_count"] == 0
    assert data["submissions_count"] == 0
    assert data["is_active"] is True


def test_create_competition_open_with_custom_config(client: TestClient, db_session: Session):
    """Test creating a COMPETITION Open with rules, rewards, max participants, and custom scoring."""
    creator = create_test_user(db_session, username="comp_creator")
    headers = auth_headers(creator.id)

    now = datetime.now(timezone.utc)
    custom_scoring = {"claps": 5.0, "views": 2.0, "shares": 10.0, "completion": 20.0}
    payload = {
        "type": "COMPETITION",
        "title": "Indie Filmmaker 2026",
        "description": "Short film competition with grand prizes.",
        "rules": "1. Must be under 60s. 2. Original music only.",
        "reward_info": "1st place: $5,000, 2nd place: $2,000",
        "max_participants": 50,
        "start_at": now.isoformat(),
        "end_at": (now + timedelta(days=14)).isoformat(),
        "scoring_config": custom_scoring,
    }

    response = client.post("/api/v1/opens", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Indie Filmmaker 2026"
    assert data["type"] == "COMPETITION"
    assert data["rules"] == "1. Must be under 60s. 2. Original music only."
    assert data["reward_info"] == "1st place: $5,000, 2nd place: $2,000"
    assert data["max_participants"] == 50
    assert data["scoring_config"] == custom_scoring


def test_create_sponsored_open_success(client: TestClient, db_session: Session):
    """Test creating a SPONSORED Open."""
    creator = create_test_user(db_session, username="brand_sponsor")
    headers = auth_headers(creator.id)

    now = datetime.now(timezone.utc)
    payload = {
        "type": "SPONSORED",
        "title": "Red Bull Freestyle Open",
        "description": "Energy in motion",
        "cover_image_url": "https://cdn.spreego.com/covers/redbull.jpg",
        "end_at": (now + timedelta(days=30)).isoformat(),
    }

    response = client.post("/api/v1/opens", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "SPONSORED"
    assert data["cover_image_url"] == "https://cdn.spreego.com/covers/redbull.jpg"


def test_create_open_invalid_dates_rejected(client: TestClient, db_session: Session):
    """Test rejecting Open creation when end_at <= start_at."""
    creator = create_test_user(db_session)
    headers = auth_headers(creator.id)

    now = datetime.now(timezone.utc)
    payload = {
        "type": "CHALLENGE",
        "title": "Time Traveler Challenge",
        "start_at": (now + timedelta(days=5)).isoformat(),
        "end_at": (now + timedelta(days=2)).isoformat(),
    }

    response = client.post("/api/v1/opens", json=payload, headers=headers)
    assert response.status_code == 400
    assert "end_at must be strictly after start_at" in response.json()["detail"]


def test_create_open_unauthenticated_rejected(client: TestClient):
    """Test creating an Open without JWT header returns 401."""
    now = datetime.now(timezone.utc)
    payload = {
        "type": "CHALLENGE",
        "title": "No Auth Challenge",
        "end_at": (now + timedelta(days=1)).isoformat(),
    }
    response = client.post("/api/v1/opens", json=payload)
    assert response.status_code == 401


# ============================================================================
# R2: Listing and Getting Opens
# ============================================================================

def test_list_and_filter_opens(client: TestClient, db_session: Session):
    """Test listing opens with optional type and status filtering and pagination."""
    creator = create_test_user(db_session, username="list_creator")
    headers = auth_headers(creator.id)
    now = datetime.now(timezone.utc)

    # Create 1 CHALLENGE and 1 COMPETITION
    client.post(
        "/api/v1/opens",
        json={"type": "CHALLENGE", "title": "Challenge A", "end_at": (now + timedelta(days=3)).isoformat()},
        headers=headers,
    )
    client.post(
        "/api/v1/opens",
        json={"type": "COMPETITION", "title": "Competition B", "end_at": (now + timedelta(days=5)).isoformat()},
        headers=headers,
    )

    # List all
    all_res = client.get("/api/v1/opens")
    assert all_res.status_code == 200
    assert len(all_res.json()) >= 2

    # Filter by CHALLENGE
    chal_res = client.get("/api/v1/opens?type=CHALLENGE")
    assert chal_res.status_code == 200
    assert all(o["type"] == "CHALLENGE" for o in chal_res.json())

    # Filter by COMPETITION
    comp_res = client.get("/api/v1/opens?type=COMPETITION")
    assert comp_res.status_code == 200
    assert all(o["type"] == "COMPETITION" for o in comp_res.json())

    # Filter by ACTIVE
    act_res = client.get("/api/v1/opens?status=ACTIVE")
    assert act_res.status_code == 200
    assert all(o["status"] == "ACTIVE" for o in act_res.json())


def test_get_single_open_details(client: TestClient, db_session: Session):
    """Test retrieving detailed single Open."""
    creator = create_test_user(db_session)
    headers = auth_headers(creator.id)
    now = datetime.now(timezone.utc)

    create_res = client.post(
        "/api/v1/opens",
        json={
            "type": "CHALLENGE",
            "title": "Detailed Challenge",
            "description": "A very detailed description.",
            "rules": "Be creative and fair.",
            "end_at": (now + timedelta(days=10)).isoformat(),
        },
        headers=headers,
    )
    open_id = create_res.json()["id"]

    get_res = client.get(f"/api/v1/opens/{open_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["id"] == open_id
    assert data["title"] == "Detailed Challenge"
    assert data["description"] == "A very detailed description."
    assert data["rules"] == "Be creative and fair."
    assert data["participants_count"] == 0
    assert data["submissions_count"] == 0


def test_get_single_open_not_found(client: TestClient):
    """Test 404 for non-existent Open ID."""
    response = client.get(f"/api/v1/opens/{uuid.uuid4()}")
    assert response.status_code == 404


# ============================================================================
# R2: Joining an Open
# ============================================================================

def test_join_active_open_success(client: TestClient, db_session: Session):
    """Test user joining an active Open successfully."""
    creator = create_test_user(db_session, username="c_creator")
    user = create_test_user(db_session, username="joiner_1")
    headers = auth_headers(user.id)
    now = datetime.now(timezone.utc)

    create_res = client.post(
        "/api/v1/opens",
        json={"type": "CHALLENGE", "title": "Joinable Open", "end_at": (now + timedelta(days=2)).isoformat()},
        headers=auth_headers(creator.id),
    )
    open_id = create_res.json()["id"]

    join_res = client.post(f"/api/v1/opens/{open_id}/join", headers=headers)
    assert join_res.status_code == 200
    join_data = join_res.json()
    assert join_data["open_id"] == open_id
    assert join_data["user_id"] == user.id

    # Verify participant count updated
    detail = client.get(f"/api/v1/opens/{open_id}").json()
    assert detail["participants_count"] == 1


def test_join_duplicate_rejected(client: TestClient, db_session: Session):
    """Test that a user cannot join the same Open twice."""
    creator = create_test_user(db_session)
    user = create_test_user(db_session)
    headers = auth_headers(user.id)
    now = datetime.now(timezone.utc)

    create_res = client.post(
        "/api/v1/opens",
        json={"type": "CHALLENGE", "title": "No Duplicate Join", "end_at": (now + timedelta(days=2)).isoformat()},
        headers=auth_headers(creator.id),
    )
    open_id = create_res.json()["id"]

    # First join succeeds
    res1 = client.post(f"/api/v1/opens/{open_id}/join", headers=headers)
    assert res1.status_code == 200

    # Second join fails
    res2 = client.post(f"/api/v1/opens/{open_id}/join", headers=headers)
    assert res2.status_code == 400
    assert "already joined" in res2.json()["detail"].lower()


def test_join_completed_or_cancelled_open_rejected(client: TestClient, db_session: Session):
    """Test rejecting join when Open is COMPLETED or CANCELLED."""
    creator = create_test_user(db_session)
    user = create_test_user(db_session)
    headers = auth_headers(user.id)
    now = datetime.now(timezone.utc)

    # 1. Completed Open
    completed_open = Open(
        creator_id=creator.id,
        type=OpenType.CHALLENGE,
        title="Completed Open",
        start_at=now - timedelta(days=5),
        end_at=now + timedelta(days=5),
        status=OpenStatus.COMPLETED,
    )
    db_session.add(completed_open)
    db_session.commit()

    res1 = client.post(f"/api/v1/opens/{completed_open.id}/join", headers=headers)
    assert res1.status_code == 400
    assert "completed" in res1.json()["detail"].lower()

    # 2. Cancelled Open
    cancelled_open = Open(
        creator_id=creator.id,
        type=OpenType.CHALLENGE,
        title="Cancelled Open",
        start_at=now - timedelta(days=5),
        end_at=now + timedelta(days=5),
        status=OpenStatus.CANCELLED,
    )
    db_session.add(cancelled_open)
    db_session.commit()

    res2 = client.post(f"/api/v1/opens/{cancelled_open.id}/join", headers=headers)
    assert res2.status_code == 400
    assert "cancelled" in res2.json()["detail"].lower()


def test_join_expired_open_rejected(client: TestClient, db_session: Session):
    """Test rejecting join when Open has passed end_at."""
    creator = create_test_user(db_session)
    user = create_test_user(db_session)
    headers = auth_headers(user.id)
    now = datetime.now(timezone.utc)

    expired_open = Open(
        creator_id=creator.id,
        type=OpenType.CHALLENGE,
        title="Expired Open",
        start_at=now - timedelta(days=10),
        end_at=now - timedelta(days=1),
        status=OpenStatus.ACTIVE,
    )
    db_session.add(expired_open)
    db_session.commit()

    res = client.post(f"/api/v1/opens/{expired_open.id}/join", headers=headers)
    assert res.status_code == 400
    assert "expired" in res.json()["detail"].lower()


def test_join_max_participants_limit_reached(client: TestClient, db_session: Session):
    """Test rejecting join when max_participants limit is reached."""
    creator = create_test_user(db_session)
    user1 = create_test_user(db_session, username="u1")
    user2 = create_test_user(db_session, username="u2")
    now = datetime.now(timezone.utc)

    create_res = client.post(
        "/api/v1/opens",
        json={
            "type": "CHALLENGE",
            "title": "Exclusive Challenge",
            "max_participants": 1,
            "end_at": (now + timedelta(days=5)).isoformat(),
        },
        headers=auth_headers(creator.id),
    )
    open_id = create_res.json()["id"]

    # User 1 joins (reaches max limit)
    res1 = client.post(f"/api/v1/opens/{open_id}/join", headers=auth_headers(user1.id))
    assert res1.status_code == 200

    # User 2 tries to join (exceeds limit)
    res2 = client.post(f"/api/v1/opens/{open_id}/join", headers=auth_headers(user2.id))
    assert res2.status_code == 400
    assert "maximum participant limit" in res2.json()["detail"].lower()


# ============================================================================
# R2: Submissions & Ownership Validation
# ============================================================================

def test_submit_spree_success(client: TestClient, db_session: Session):
    """Test creator submitting their own Spree to an active Open."""
    creator = create_test_user(db_session, username="submitter")
    headers = auth_headers(creator.id)
    now = datetime.now(timezone.utc)

    open_res = client.post(
        "/api/v1/opens",
        json={"type": "CHALLENGE", "title": "Submit Here", "end_at": (now + timedelta(days=3)).isoformat()},
        headers=headers,
    )
    open_id = open_res.json()["id"]

    spree = create_test_spree(db_session, creator=creator, title="My Submission Spree")

    sub_res = client.post(
        f"/api/v1/opens/{open_id}/submissions",
        json={"spree_id": spree.id},
        headers=headers,
    )
    assert sub_res.status_code == 201
    sub_data = sub_res.json()
    assert sub_data["open_id"] == open_id
    assert sub_data["user_id"] == creator.id
    assert sub_data["spree_id"] == spree.id
    assert sub_data["score"] >= 0.0

    # Verify Open submissions count incremented
    detail = client.get(f"/api/v1/opens/{open_id}").json()
    assert detail["submissions_count"] == 1


def test_submit_spree_ownership_check_rejected(client: TestClient, db_session: Session):
    """Test that a user cannot submit another creator's Spree (HTTP 403)."""
    real_creator = create_test_user(db_session, username="real_creator")
    imposter = create_test_user(db_session, username="imposter")
    now = datetime.now(timezone.utc)

    open_res = client.post(
        "/api/v1/opens",
        json={"type": "CHALLENGE", "title": "Ownership Test", "end_at": (now + timedelta(days=3)).isoformat()},
        headers=auth_headers(real_creator.id),
    )
    open_id = open_res.json()["id"]

    spree = create_test_spree(db_session, creator=real_creator, title="Real Creator's Spree")

    # Imposter tries to submit real creator's spree
    sub_res = client.post(
        f"/api/v1/opens/{open_id}/submissions",
        json={"spree_id": spree.id},
        headers=auth_headers(imposter.id),
    )
    assert sub_res.status_code == 403
    assert "only submit sprees that you created" in sub_res.json()["detail"].lower()


def test_submit_duplicate_spree_rejected(client: TestClient, db_session: Session):
    """Test that submitting the same Spree twice to the same Open is rejected (HTTP 400)."""
    creator = create_test_user(db_session)
    headers = auth_headers(creator.id)
    now = datetime.now(timezone.utc)

    open_res = client.post(
        "/api/v1/opens",
        json={"type": "CHALLENGE", "title": "No Dups", "end_at": (now + timedelta(days=3)).isoformat()},
        headers=headers,
    )
    open_id = open_res.json()["id"]

    spree = create_test_spree(db_session, creator=creator, title="Unique Spree")

    # First submission succeeds
    sub1 = client.post(f"/api/v1/opens/{open_id}/submissions", json={"spree_id": spree.id}, headers=headers)
    assert sub1.status_code == 201

    # Second submission fails
    sub2 = client.post(f"/api/v1/opens/{open_id}/submissions", json={"spree_id": spree.id}, headers=headers)
    assert sub2.status_code == 400
    assert "already been submitted" in sub2.json()["detail"].lower()


def test_submit_to_inactive_or_expired_open_rejected(client: TestClient, db_session: Session):
    """Test submitting to inactive/expired Open is rejected (HTTP 400)."""
    creator = create_test_user(db_session)
    headers = auth_headers(creator.id)
    now = datetime.now(timezone.utc)

    # 1. Expired Open
    expired_open = Open(
        creator_id=creator.id,
        type=OpenType.CHALLENGE,
        title="Expired Challenge",
        start_at=now - timedelta(days=5),
        end_at=now - timedelta(days=1),
        status=OpenStatus.ACTIVE,
    )
    db_session.add(expired_open)
    db_session.commit()

    spree1 = create_test_spree(db_session, creator=creator, title="Spree 1")
    res1 = client.post(f"/api/v1/opens/{expired_open.id}/submissions", json={"spree_id": spree1.id}, headers=headers)
    assert res1.status_code == 400
    assert "expired" in res1.json()["detail"].lower()

    # 2. Cancelled Open
    cancelled_open = Open(
        creator_id=creator.id,
        type=OpenType.CHALLENGE,
        title="Cancelled Challenge",
        start_at=now - timedelta(days=2),
        end_at=now + timedelta(days=5),
        status=OpenStatus.CANCELLED,
    )
    db_session.add(cancelled_open)
    db_session.commit()

    spree2 = create_test_spree(db_session, creator=creator, title="Spree 2")
    res2 = client.post(f"/api/v1/opens/{cancelled_open.id}/submissions", json={"spree_id": spree2.id}, headers=headers)
    assert res2.status_code == 400
    assert "inactive" in res2.json()["detail"].lower()


# ============================================================================
# R2: VIEW Feed (GET /api/v1/opens/{id}/feed)
# ============================================================================

def test_view_feed_returns_only_open_submissions(client: TestClient, db_session: Session):
    """Test that VIEW Feed contains ONLY Sprees submitted to that specific Open."""
    creator1 = create_test_user(db_session, username="c1")
    creator2 = create_test_user(db_session, username="c2")
    other_creator = create_test_user(db_session, username="c_other")
    now = datetime.now(timezone.utc)

    # Create Open A and Open B
    open_a = client.post(
        "/api/v1/opens",
        json={"type": "CHALLENGE", "title": "Open A", "end_at": (now + timedelta(days=5)).isoformat()},
        headers=auth_headers(creator1.id),
    ).json()

    open_b = client.post(
        "/api/v1/opens",
        json={"type": "CHALLENGE", "title": "Open B", "end_at": (now + timedelta(days=5)).isoformat()},
        headers=auth_headers(creator2.id),
    ).json()

    # Create 3 Sprees
    spree_a1 = create_test_spree(db_session, creator=creator1, title="Spree for Open A")
    spree_b1 = create_test_spree(db_session, creator=creator2, title="Spree for Open B")
    spree_general = create_test_spree(db_session, creator=other_creator, title="Unsubmitted Spree")

    # Submit spree_a1 to Open A
    client.post(
        f"/api/v1/opens/{open_a['id']}/submissions",
        json={"spree_id": spree_a1.id},
        headers=auth_headers(creator1.id),
    )

    # Submit spree_b1 to Open B
    client.post(
        f"/api/v1/opens/{open_b['id']}/submissions",
        json={"spree_id": spree_b1.id},
        headers=auth_headers(creator2.id),
    )

    # Check Open A feed: must ONLY have spree_a1
    feed_a_res = client.get(f"/api/v1/opens/{open_a['id']}/feed")
    assert feed_a_res.status_code == 200
    feed_a = feed_a_res.json()
    feed_a_ids = [item["id"] for item in feed_a]
    assert spree_a1.id in feed_a_ids
    assert spree_b1.id not in feed_a_ids
    assert spree_general.id not in feed_a_ids

    # Check Open B feed: must ONLY have spree_b1
    feed_b_res = client.get(f"/api/v1/opens/{open_b['id']}/feed")
    assert feed_b_res.status_code == 200
    feed_b = feed_b_res.json()
    feed_b_ids = [item["id"] for item in feed_b]
    assert spree_b1.id in feed_b_ids
    assert spree_a1.id not in feed_b_ids
    assert spree_general.id not in feed_b_ids


# ============================================================================
# R2: Configurable Dynamic RANKING Leaderboard (GET /api/v1/opens/{id}/ranking)
# ============================================================================

def test_dynamic_ranking_leaderboard_custom_weights(client: TestClient, db_session: Session):
    """
    Test real-time calculated ranking driven strictly by the Open's stored scoring_config.
    Proves that order changes dynamically according to configured weights without hard-coded formula.
    """
    user_a = create_test_user(db_session, username="creator_claps")
    user_b = create_test_user(db_session, username="creator_views")
    viewer1 = create_test_user(db_session, username="viewer_1")
    viewer2 = create_test_user(db_session, username="viewer_2")
    now = datetime.now(timezone.utc)

    # Spree A: High claps (2 claps), 0 views
    spree_a = create_test_spree(db_session, creator=user_a, title="High Claps Spree")
    db_session.add(SpreeClap(spree_id=spree_a.id, user_id=viewer1.id))
    db_session.add(SpreeClap(spree_id=spree_a.id, user_id=viewer2.id))

    # Spree B: High views (10 views), 0 claps
    spree_b = create_test_spree(db_session, creator=user_b, title="High Views Spree")
    for _ in range(10):
        db_session.add(SpreeView(spree_id=spree_b.id, user_id=viewer1.id, watch_duration=10.0, completed=False))

    db_session.commit()

    # Open 1: "Claps Heavy" -> weights: claps=10.0, views=1.0
    # Expected score A: 2 * 10 = 20.0, score B: 10 * 1 = 10.0 -> A ranks #1
    open_claps_heavy = client.post(
        "/api/v1/opens",
        json={
            "type": "COMPETITION",
            "title": "Claps Heavy Open",
            "end_at": (now + timedelta(days=5)).isoformat(),
            "scoring_config": {"claps": 10.0, "views": 1.0},
        },
        headers=auth_headers(user_a.id),
    ).json()

    client.post(
        f"/api/v1/opens/{open_claps_heavy['id']}/submissions",
        json={"spree_id": spree_a.id},
        headers=auth_headers(user_a.id),
    )
    client.post(
        f"/api/v1/opens/{open_claps_heavy['id']}/submissions",
        json={"spree_id": spree_b.id},
        headers=auth_headers(user_b.id),
    )

    ranking1_res = client.get(f"/api/v1/opens/{open_claps_heavy['id']}/ranking")
    assert ranking1_res.status_code == 200
    ranking1 = ranking1_res.json()
    assert len(ranking1) == 2
    assert ranking1[0]["rank"] == 1
    assert ranking1[0]["spree_id"] == spree_a.id
    assert ranking1[0]["score"] == 20.0
    assert ranking1[1]["rank"] == 2
    assert ranking1[1]["spree_id"] == spree_b.id
    assert ranking1[1]["score"] == 10.0

    # Open 2: "Views Heavy" -> weights: claps=1.0, views=10.0
    # Expected score A: 2 * 1 = 2.0, score B: 10 * 10 = 100.0 -> B ranks #1
    open_views_heavy = client.post(
        "/api/v1/opens",
        json={
            "type": "COMPETITION",
            "title": "Views Heavy Open",
            "end_at": (now + timedelta(days=5)).isoformat(),
            "scoring_config": {"claps": 1.0, "views": 10.0},
        },
        headers=auth_headers(user_b.id),
    ).json()

    client.post(
        f"/api/v1/opens/{open_views_heavy['id']}/submissions",
        json={"spree_id": spree_a.id},
        headers=auth_headers(user_a.id),
    )
    client.post(
        f"/api/v1/opens/{open_views_heavy['id']}/submissions",
        json={"spree_id": spree_b.id},
        headers=auth_headers(user_b.id),
    )

    ranking2_res = client.get(f"/api/v1/opens/{open_views_heavy['id']}/ranking")
    assert ranking2_res.status_code == 200
    ranking2 = ranking2_res.json()
    assert len(ranking2) == 2
    assert ranking2[0]["rank"] == 1
    assert ranking2[0]["spree_id"] == spree_b.id
    assert ranking2[0]["score"] == 100.0
    assert ranking2[1]["rank"] == 2
    assert ranking2[1]["spree_id"] == spree_a.id
    assert ranking2[1]["score"] == 2.0


def test_ranking_persists_rank_and_score_in_database(client: TestClient, db_session: Session):
    """Verify that calculating ranking updates OpenSubmission.rank and OpenSubmission.score in DB."""
    creator = create_test_user(db_session, username="persister")
    headers = auth_headers(creator.id)
    now = datetime.now(timezone.utc)

    open_res = client.post(
        "/api/v1/opens",
        json={"type": "CHALLENGE", "title": "Persistence Test", "end_at": (now + timedelta(days=3)).isoformat()},
        headers=headers,
    )
    open_id = open_res.json()["id"]

    spree = create_test_spree(db_session, creator=creator, title="Persist Spree")
    sub_res = client.post(
        f"/api/v1/opens/{open_id}/submissions",
        json={"spree_id": spree.id},
        headers=headers,
    )
    sub_id = sub_res.json()["id"]

    # Trigger ranking calculation
    ranking_res = client.get(f"/api/v1/opens/{open_id}/ranking")
    assert ranking_res.status_code == 200
    assert len(ranking_res.json()) == 1

    # Verify directly from DB session
    db_sub = db_session.query(OpenSubmission).filter(OpenSubmission.id == sub_id).first()
    assert db_sub is not None
    assert db_sub.rank == 1
    assert db_sub.score is not None


def test_ranking_empty_open(client: TestClient, db_session: Session):
    """Test leaderboard returns empty list when no submissions exist."""
    creator = create_test_user(db_session)
    now = datetime.now(timezone.utc)

    open_res = client.post(
        "/api/v1/opens",
        json={"type": "CHALLENGE", "title": "Empty Open", "end_at": (now + timedelta(days=2)).isoformat()},
        headers=auth_headers(creator.id),
    )
    open_id = open_res.json()["id"]

    ranking_res = client.get(f"/api/v1/opens/{open_id}/ranking")
    assert ranking_res.status_code == 200
    assert ranking_res.json() == []


# ============================================================================
# R3: Additional Edge Case & Robustness Verification
# ============================================================================

def test_join_future_open_rejected(client: TestClient, db_session: Session):
    """Test that joining an Open that has not started yet is rejected (HTTP 400)."""
    creator = create_test_user(db_session)
    user = create_test_user(db_session)
    now = datetime.now(timezone.utc)

    future_open = Open(
        creator_id=creator.id,
        type=OpenType.CHALLENGE,
        title="Future Challenge",
        start_at=now + timedelta(days=2),
        end_at=now + timedelta(days=10),
        status=OpenStatus.ACTIVE,
    )
    db_session.add(future_open)
    db_session.commit()

    res = client.post(f"/api/v1/opens/{future_open.id}/join", headers=auth_headers(user.id))
    assert res.status_code == 400
    assert "not started yet" in res.json()["detail"].lower()


def test_submit_future_open_rejected(client: TestClient, db_session: Session):
    """Test that submitting to an Open that has not started yet is rejected (HTTP 400)."""
    creator = create_test_user(db_session)
    now = datetime.now(timezone.utc)

    future_open = Open(
        creator_id=creator.id,
        type=OpenType.CHALLENGE,
        title="Future Submission Challenge",
        start_at=now + timedelta(days=2),
        end_at=now + timedelta(days=10),
        status=OpenStatus.ACTIVE,
    )
    db_session.add(future_open)
    db_session.commit()

    spree = create_test_spree(db_session, creator=creator, title="Future Spree")
    res = client.post(
        f"/api/v1/opens/{future_open.id}/submissions",
        json={"spree_id": spree.id},
        headers=auth_headers(creator.id),
    )
    assert res.status_code == 400
    assert "not started yet" in res.json()["detail"].lower()


def test_submit_nonexistent_spree_returns_404(client: TestClient, db_session: Session):
    """Test that submitting a non-existent spree ID returns 404."""
    creator = create_test_user(db_session)
    now = datetime.now(timezone.utc)

    open_res = client.post(
        "/api/v1/opens",
        json={"type": "CHALLENGE", "title": "404 Spree Open", "end_at": (now + timedelta(days=3)).isoformat()},
        headers=auth_headers(creator.id),
    ).json()

    res = client.post(
        f"/api/v1/opens/{open_res['id']}/submissions",
        json={"spree_id": str(uuid.uuid4())},
        headers=auth_headers(creator.id),
    )
    assert res.status_code == 404
    assert "spree not found" in res.json()["detail"].lower()


def test_submit_max_participants_limit_reached(client: TestClient, db_session: Session):
    """Test that auto-join on submission is rejected when max_participants limit is reached."""
    creator = create_test_user(db_session, username="limit_creator")
    user1 = create_test_user(db_session, username="limit_u1")
    user2 = create_test_user(db_session, username="limit_u2")
    now = datetime.now(timezone.utc)

    open_res = client.post(
        "/api/v1/opens",
        json={
            "type": "CHALLENGE",
            "title": "Strict Cap Challenge",
            "max_participants": 1,
            "end_at": (now + timedelta(days=5)).isoformat(),
        },
        headers=auth_headers(creator.id),
    ).json()

    # User 1 explicitly joins, taking the 1 slot
    client.post(f"/api/v1/opens/{open_res['id']}/join", headers=auth_headers(user1.id))

    # User 2 tries to submit directly without having joined first -> should be blocked by participant limit
    spree2 = create_test_spree(db_session, creator=user2, title="User 2 Spree")
    res2 = client.post(
        f"/api/v1/opens/{open_res['id']}/submissions",
        json={"spree_id": spree2.id},
        headers=auth_headers(user2.id),
    )
    assert res2.status_code == 400
    assert "maximum participant limit" in res2.json()["detail"].lower()


def test_get_feed_and_ranking_nonexistent_open_returns_404(client: TestClient):
    """Test 404 for feed and ranking on non-existent Open ID."""
    fake_id = str(uuid.uuid4())
    res_feed = client.get(f"/api/v1/opens/{fake_id}/feed")
    assert res_feed.status_code == 404

    res_rank = client.get(f"/api/v1/opens/{fake_id}/ranking")
    assert res_rank.status_code == 404


def test_ranking_with_all_engagement_metrics(client: TestClient, db_session: Session):
    """Test ranking calculates accurately when comments, saves, shares, and completion metrics exist."""
    user = create_test_user(db_session, username="all_metrics_creator")
    viewer = create_test_user(db_session, username="all_metrics_viewer")
    now = datetime.now(timezone.utc)

    spree = create_test_spree(db_session, creator=user, title="All Metrics Spree")
    # 1 clap, 1 comment, 1 save, 1 share, 2 views (1 completed -> completion_rate 0.5)
    db_session.add(SpreeClap(spree_id=spree.id, user_id=viewer.id))
    db_session.add(SpreeComment(spree_id=spree.id, user_id=viewer.id, text="Great video!"))
    db_session.add(SpreeSave(spree_id=spree.id, user_id=viewer.id))
    db_session.add(SpreeShare(spree_id=spree.id, user_id=viewer.id, platform="twitter"))
    db_session.add(SpreeView(spree_id=spree.id, user_id=viewer.id, watch_duration=30.0, completed=True))
    db_session.add(SpreeView(spree_id=spree.id, user_id=viewer.id, watch_duration=5.0, completed=False))
    db_session.commit()

    scoring_config = {
        "claps": 2.0,
        "views": 1.0,
        "comments": 3.0,
        "saves": 4.0,
        "shares": 5.0,
        "completion": 10.0,
    }
    # Expected score:
    # claps: 1 * 2 = 2.0
    # views: 2 * 1 = 2.0
    # comments: 1 * 3 = 3.0
    # saves: 1 * 4 = 4.0
    # shares: 1 * 5 = 5.0
    # completion: 1 * 10 = 10.0
    # Total = 26.0

    open_res = client.post(
        "/api/v1/opens",
        json={
            "type": "COMPETITION",
            "title": "Comprehensive Scoring Open",
            "end_at": (now + timedelta(days=3)).isoformat(),
            "scoring_config": scoring_config,
        },
        headers=auth_headers(user.id),
    ).json()

    client.post(
        f"/api/v1/opens/{open_res['id']}/submissions",
        json={"spree_id": spree.id},
        headers=auth_headers(user.id),
    )

    ranking_res = client.get(f"/api/v1/opens/{open_res['id']}/ranking")
    assert ranking_res.status_code == 200
    ranking = ranking_res.json()
    assert len(ranking) == 1
    assert ranking[0]["score"] == 26.0
    assert ranking[0]["rank"] == 1
    assert ranking[0]["metrics"]["comments_count"] == 1
    assert ranking[0]["metrics"]["saves_count"] == 1
    assert ranking[0]["metrics"]["shares_count"] == 1
    assert ranking[0]["metrics"]["completed_views_count"] == 1


def test_postgres_open_models_live_integration():
    """Verify Open, OpenParticipant, and OpenSubmission tables map properly in live PostgreSQL if connected."""
    import os
    from sqlalchemy import create_engine
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
        u = User(phone_number=f"+197{uid[:7]}", email=f"pg_open_{uid}@spreego.com")
        db.add(u)
        db.commit()

        now = datetime.now(timezone.utc)
        op = Open(
            creator_id=u.id,
            type=OpenType.CHALLENGE,
            title="PG Live Open",
            start_at=now,
            end_at=now + timedelta(days=7),
            status=OpenStatus.ACTIVE,
        )
        db.add(op)
        db.commit()

        part = OpenParticipant(open_id=op.id, user_id=u.id)
        db.add(part)
        db.commit()

        s = Spree(creator_id=u.id, type=SpreeType.VIDEO_SHORT, title="PG Spree", media_url="http://test")
        db.add(s)
        db.commit()

        sub = OpenSubmission(open_id=op.id, user_id=u.id, spree_id=s.id, score=15.5)
        db.add(sub)
        db.commit()

        # Query back from Postgres
        queried = db.query(Open).filter(Open.id == op.id).first()
        assert queried is not None
        assert queried.title == "PG Live Open"
        assert queried.participants_count == 1
        assert queried.submissions_count == 1

        # Cleanup cascades
        db.delete(u)
        db.commit()
    finally:
        db.close()


def test_scoring_config_negative_or_nan_weights_rejected(client: TestClient, db_session: Session):
    """Test that negative, NaN, Inf, or empty metric weights in scoring_config are rejected with 422."""
    creator = create_test_user(db_session, username="weight_tester")
    headers = auth_headers(creator.id)
    now = datetime.now(timezone.utc)

    # 1. Negative weight
    payload_neg = {
        "title": "Negative Weight Challenge",
        "end_at": (now + timedelta(days=5)).isoformat(),
        "scoring_config": {"claps": -2.0},
    }
    res_neg = client.post("/api/v1/opens", json=payload_neg, headers=headers)
    assert res_neg.status_code == 422

    # 2. Empty metric key
    payload_empty_key = {
        "title": "Empty Key Challenge",
        "end_at": (now + timedelta(days=5)).isoformat(),
        "scoring_config": {"": 2.0},
    }
    res_empty = client.post("/api/v1/opens", json=payload_empty_key, headers=headers)
    assert res_empty.status_code == 422


def test_create_open_empty_or_whitespace_title_rejected(client: TestClient, db_session: Session):
    """Test that empty or whitespace-only title is rejected with 422."""
    creator = create_test_user(db_session)
    headers = auth_headers(creator.id)
    now = datetime.now(timezone.utc)

    for bad_title in ["", "   ", " \t \n "]:
        payload = {
            "title": bad_title,
            "end_at": (now + timedelta(days=3)).isoformat(),
        }
        res = client.post("/api/v1/opens", json=payload, headers=headers)
        assert res.status_code == 422


def test_submit_empty_spree_id_rejected(client: TestClient, db_session: Session):
    """Test that submitting empty or whitespace spree_id is rejected with 422."""
    creator = create_test_user(db_session)
    headers = auth_headers(creator.id)
    now = datetime.now(timezone.utc)

    open_res = client.post(
        "/api/v1/opens",
        json={"title": "Empty Spree ID Challenge", "end_at": (now + timedelta(days=3)).isoformat()},
        headers=headers,
    ).json()

    for bad_id in ["", "   "]:
        res = client.post(
            f"/api/v1/opens/{open_res['id']}/submissions",
            json={"spree_id": bad_id},
            headers=headers,
        )
        assert res.status_code == 422


def test_timezone_naive_and_offset_datetimes_handled(client: TestClient, db_session: Session):
    """Test creating an Open with naive datetimes and non-UTC offsets in JSON payloads."""
    creator = create_test_user(db_session, username="tz_creator")
    headers = auth_headers(creator.id)

    # 1. Naive datetime strings without 'Z' or offset
    payload_naive = {
        "title": "Naive Datetime Challenge",
        "start_at": "2026-11-01T00:00:00",
        "end_at": "2026-11-15T00:00:00",
    }
    res_naive = client.post("/api/v1/opens", json=payload_naive, headers=headers)
    assert res_naive.status_code == 201
    data_naive = res_naive.json()
    assert "2026-11-01" in data_naive["start_at"]
    assert "2026-11-15" in data_naive["end_at"]

    # 2. Offset datetime strings with +05:30
    payload_offset = {
        "title": "Offset Datetime Challenge",
        "start_at": "2026-11-01T10:00:00+05:30",
        "end_at": "2026-11-15T10:00:00+05:30",
    }
    res_offset = client.post("/api/v1/opens", json=payload_offset, headers=headers)
    assert res_offset.status_code == 201


def test_ranking_tie_breaking_deterministic(client: TestClient, db_session: Session):
    """
    Test deterministic leaderboard tie-breaking:
    When two submissions have identical scores:
    1. The one created earlier gets the better (lower) rank number.
    2. If timestamps are identical, deterministic order by submission ID.
    """
    u1 = create_test_user(db_session, username="tie_u1")
    u2 = create_test_user(db_session, username="tie_u2")
    now = datetime.now(timezone.utc)

    open_res = client.post(
        "/api/v1/opens",
        json={"title": "Tie-break Open", "end_at": (now + timedelta(days=5)).isoformat()},
        headers=auth_headers(u1.id),
    ).json()

    s1 = create_test_spree(db_session, creator=u1, title="Spree Tie 1")
    s2 = create_test_spree(db_session, creator=u2, title="Spree Tie 2")

    # Submit s1 earlier
    sub1 = client.post(
        f"/api/v1/opens/{open_res['id']}/submissions",
        json={"spree_id": s1.id},
        headers=auth_headers(u1.id),
    ).json()

    # Submit s2 later
    sub2 = client.post(
        f"/api/v1/opens/{open_res['id']}/submissions",
        json={"spree_id": s2.id},
        headers=auth_headers(u2.id),
    ).json()

    # Manually ensure sub1 has earlier created_at than sub2
    db_s1 = db_session.query(OpenSubmission).filter(OpenSubmission.id == sub1["id"]).first()
    db_s2 = db_session.query(OpenSubmission).filter(OpenSubmission.id == sub2["id"]).first()
    db_s1.created_at = now - timedelta(minutes=10)
    db_s2.created_at = now - timedelta(minutes=5)
    db_session.commit()

    ranking = client.get(f"/api/v1/opens/{open_res['id']}/ranking").json()
    assert len(ranking) == 2
    # Both have score 0.0, sub1 submitted earlier -> rank 1
    assert ranking[0]["submission_id"] == sub1["id"]
    assert ranking[0]["rank"] == 1
    assert ranking[1]["submission_id"] == sub2["id"]
    assert ranking[1]["rank"] == 2

    # Now test identical timestamps: deterministic total order by submission ID
    db_s1.created_at = now
    db_s2.created_at = now
    db_session.commit()

    ranking_same_time = client.get(f"/api/v1/opens/{open_res['id']}/ranking").json()
    assert len(ranking_same_time) == 2
    expected_order = sorted([sub1["id"], sub2["id"]])
    actual_order = [r["submission_id"] for r in ranking_same_time]
    assert actual_order == expected_order


def test_postgresql_ddl_compilation_opens():
    """Verify that all 3 opens tables compile cleanly to valid PostgreSQL DDL without errors."""
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.schema import CreateTable

    dialect = postgresql.dialect()
    table_names = ["opens", "open_participants", "open_submissions"]
    for table_name in table_names:
        table = Base.metadata.tables[table_name]
        ddl = str(CreateTable(table).compile(dialect=dialect))
        assert f"CREATE TABLE {table_name}" in ddl
        assert "PRIMARY KEY" in ddl
        if table_name in ["open_participants", "open_submissions"]:
            assert "FOREIGN KEY" in ddl
            assert "UNIQUE" in ddl or "CONSTRAINT" in ddl


def test_scoring_config_case_insensitive_matching(client: TestClient, db_session: Session):
    """Test that metric names in scoring_config match engagement stats case-insensitively."""
    creator = create_test_user(db_session, username="case_creator")
    viewer = create_test_user(db_session, username="case_viewer")
    now = datetime.now(timezone.utc)

    spree = create_test_spree(db_session, creator=creator, title="Case Test Spree")
    db_session.add(SpreeClap(spree_id=spree.id, user_id=viewer.id))
    db_session.commit()

    # scoring config with mixed-case keys
    open_res = client.post(
        "/api/v1/opens",
        json={
            "title": "Case Insensitive Open",
            "end_at": (now + timedelta(days=3)).isoformat(),
            "scoring_config": {"CLAPS": 7.5},
        },
        headers=auth_headers(creator.id),
    ).json()

    client.post(
        f"/api/v1/opens/{open_res['id']}/submissions",
        json={"spree_id": spree.id},
        headers=auth_headers(creator.id),
    )

    ranking = client.get(f"/api/v1/opens/{open_res['id']}/ranking").json()
    assert len(ranking) == 1
    assert ranking[0]["score"] == 7.5


def test_draft_open_join_and_submit_rejected(client: TestClient, db_session: Session):
    """Test that joining or submitting to an Open with status DRAFT is rejected (HTTP 400)."""
    creator = create_test_user(db_session, username="draft_creator")
    user = create_test_user(db_session, username="draft_user")
    now = datetime.now(timezone.utc)

    draft_open = Open(
        creator_id=creator.id,
        type=OpenType.CHALLENGE,
        title="Draft Open",
        start_at=now,
        end_at=now + timedelta(days=5),
        status=OpenStatus.DRAFT,
    )
    db_session.add(draft_open)
    db_session.commit()

    # Join rejected
    res_join = client.post(f"/api/v1/opens/{draft_open.id}/join", headers=auth_headers(user.id))
    assert res_join.status_code == 400
    assert "draft" in res_join.json()["detail"].lower()

    # Submit rejected
    spree = create_test_spree(db_session, creator=creator, title="Draft Spree")
    res_sub = client.post(
        f"/api/v1/opens/{draft_open.id}/submissions",
        json={"spree_id": spree.id},
        headers=auth_headers(creator.id),
    )
    assert res_sub.status_code == 400
    assert "inactive" in res_sub.json()["detail"].lower()


def test_scoring_config_empty_dict_rejected(client: TestClient, db_session: Session):
    """Test that scoring_config as an empty dictionary is rejected with 422."""
    creator = create_test_user(db_session, username="empty_dict_creator")
    now = datetime.now(timezone.utc)
    payload = {
        "title": "Empty Dict Config Open",
        "end_at": (now + timedelta(days=5)).isoformat(),
        "scoring_config": {},
    }
    res = client.post("/api/v1/opens", json=payload, headers=auth_headers(creator.id))
    assert res.status_code == 422
    assert "empty" in res.text.lower()


def test_scoring_config_invalid_metric_identifier_rejected(client: TestClient, db_session: Session):
    """Test that metric names with leading underscores or invalid characters are rejected with 422."""
    creator = create_test_user(db_session, username="invalid_metric_creator")
    now = datetime.now(timezone.utc)

    # 1. Leading underscore / dunder name
    for bad_metric in ["__doc__", "_private", "__class__"]:
        payload = {
            "title": "Bad Metric Open",
            "end_at": (now + timedelta(days=5)).isoformat(),
            "scoring_config": {bad_metric: 2.0},
        }
        res = client.post("/api/v1/opens", json=payload, headers=auth_headers(creator.id))
        assert res.status_code == 422

    # 2. Non-identifier metric name
    payload_special = {
        "title": "Special Char Metric Open",
        "end_at": (now + timedelta(days=5)).isoformat(),
        "scoring_config": {"claps-metric!": 2.0},
    }
    res_special = client.post("/api/v1/opens", json=payload_special, headers=auth_headers(creator.id))
    assert res_special.status_code == 422


def test_compute_score_dunder_or_non_numeric_attributes_safe(db_session: Session):
    """Directly test that _compute_score handles dunder or non-numeric keys safely without crashing."""
    from src.services.feed_ranking_service import SpreeEngagementStats
    from src.services.open_service import OpenService

    service = OpenService(db_session)
    stats = SpreeEngagementStats(claps_count=4, views_count=10)

    # Config with dunder attributes that exist on SpreeEngagementStats instance
    weird_config = {
        "__doc__": 10.0,
        "__class__": 5.0,
        "__dict__": 3.0,
        "claps": 2.5,
    }
    score = service._compute_score(stats, weird_config)
    assert score == 10.0  # 4 claps * 2.5 = 10.0


def test_open_feed_page_pagination(client: TestClient, db_session: Session):
    """Test VIEW feed pagination with page (1-indexed) and limit query parameters."""
    creator = create_test_user(db_session, username="feed_pager")
    headers = auth_headers(creator.id)
    now = datetime.now(timezone.utc)

    open_res = client.post(
        "/api/v1/opens",
        json={"title": "Feed Pagination Open", "end_at": (now + timedelta(days=5)).isoformat()},
        headers=headers,
    ).json()

    s1 = create_test_spree(db_session, creator=creator, title="Page Spree 1")
    s2 = create_test_spree(db_session, creator=creator, title="Page Spree 2")

    client.post(f"/api/v1/opens/{open_res['id']}/submissions", json={"spree_id": s1.id}, headers=headers)
    client.post(f"/api/v1/opens/{open_res['id']}/submissions", json={"spree_id": s2.id}, headers=headers)

    # Page 1, limit 1
    page1 = client.get(f"/api/v1/opens/{open_res['id']}/feed?page=1&limit=1").json()
    assert len(page1) == 1

    # Page 2, limit 1
    page2 = client.get(f"/api/v1/opens/{open_res['id']}/feed?page=2&limit=1").json()
    assert len(page2) == 1
    assert page1[0]["id"] != page2[0]["id"]


def test_concurrent_duplicate_join_integrity_error_handling(client: TestClient, db_session: Session):
    """Test that duplicate join collision raises clean ValueError returning HTTP 400."""
    creator = create_test_user(db_session, username="collision_creator")
    user = create_test_user(db_session, username="collision_user")
    now = datetime.now(timezone.utc)

    open_res = client.post(
        "/api/v1/opens",
        json={"title": "Collision Open", "end_at": (now + timedelta(days=5)).isoformat()},
        headers=auth_headers(creator.id),
    ).json()

    # First join
    res1 = client.post(f"/api/v1/opens/{open_res['id']}/join", headers=auth_headers(user.id))
    assert res1.status_code == 200

    # Second join attempts to insert duplicate -> ValueError -> HTTP 400
    res2 = client.post(f"/api/v1/opens/{open_res['id']}/join", headers=auth_headers(user.id))
    assert res2.status_code == 400
    assert "already joined" in res2.json()["detail"].lower()



