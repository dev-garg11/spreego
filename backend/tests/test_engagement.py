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
    full_name: str = None,
    avatar_url: str = "https://cdn.spreego.com/avatars/default.png",
    is_active: bool = True,
) -> User:
    """Helper to provision a verified user with profile directly into test DB."""
    uid = str(uuid.uuid4())[:8]
    phone = phone_number or f"+188{uid[:7]}"
    mail = email or f"eng_{uid}@spreego.com"
    handle = username or f"user_{uid}"
    name = full_name or f"User {handle}"

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
        full_name=name,
        avatar_url=avatar_url,
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
    title: str = "Engagement Test Spree",
    visibility: SpreeVisibility = SpreeVisibility.PUBLIC,
) -> Spree:
    """Helper to create a test Spree."""
    spree = Spree(
        creator_id=creator.id,
        type=SpreeType.VIDEO_SHORT,
        title=title,
        media_url="https://cdn.spreego.com/videos/test.mp4",
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

def test_engagement_models_registered_on_metadata():
    """Verify all 5 engagement tables are registered on Base.metadata with proper constraints."""
    table_names = Base.metadata.tables.keys()
    assert "spree_views" in table_names
    assert "spree_claps" in table_names
    assert "spree_comments" in table_names
    assert "spree_saves" in table_names
    assert "spree_shares" in table_names

    # Verify unique constraint on spree_claps (spree_id, user_id)
    claps_table = Base.metadata.tables["spree_claps"]
    claps_unique = [c.name for c in claps_table.constraints if hasattr(c, "columns") and len(c.columns) == 2]
    assert "uq_spree_claps_spree_user" in claps_unique

    # Verify unique constraint on spree_saves (spree_id, user_id)
    saves_table = Base.metadata.tables["spree_saves"]
    saves_unique = [c.name for c in saves_table.constraints if hasattr(c, "columns") and len(c.columns) == 2]
    assert "uq_spree_saves_spree_user" in saves_unique


# ============================================================================
# R2: Views Endpoint (POST /api/v1/sprees/{id}/view)
# ============================================================================

def test_record_view_anonymous_success(client: TestClient, db_session: Session):
    """Test recording an anonymous view with watch duration and completion."""
    creator = create_test_user(db_session, username="creator_view_1")
    spree = create_test_spree(db_session, creator)

    payload = {"watch_duration": 28.5, "completed": True}
    response = client.post(f"/api/v1/sprees/{spree.id}/view", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["spree_id"] == spree.id
    assert data["user_id"] is None
    assert data["watch_duration"] == 28.5
    assert data["completed"] is True
    assert "id" in data


def test_record_view_authenticated_success(client: TestClient, db_session: Session):
    """Test recording an authenticated view binds the user_id."""
    creator = create_test_user(db_session, username="creator_view_2")
    viewer = create_test_user(db_session, username="viewer_view_2")
    spree = create_test_spree(db_session, creator)

    payload = {"watch_duration": 15.0, "completed": False}
    response = client.post(
        f"/api/v1/sprees/{spree.id}/view",
        json=payload,
        headers=auth_headers(viewer.id),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["spree_id"] == spree.id
    assert data["user_id"] == viewer.id
    assert data["watch_duration"] == 15.0
    assert data["completed"] is False


def test_record_view_default_payload(client: TestClient, db_session: Session):
    """Test recording a view with empty payload or no body defaults to 0.0s and completed=False."""
    creator = create_test_user(db_session, username="creator_view_3")
    spree = create_test_spree(db_session, creator)

    response = client.post(f"/api/v1/sprees/{spree.id}/view", json={})
    assert response.status_code == 200
    data = response.json()
    assert data["watch_duration"] == 0.0
    assert data["completed"] is False

    # Also test posting with null/no body
    resp_no_body = client.post(f"/api/v1/sprees/{spree.id}/view")
    assert resp_no_body.status_code == 200
    assert resp_no_body.json()["watch_duration"] == 0.0


def test_record_view_nonexistent_spree(client: TestClient, db_session: Session):
    """Test recording a view on a non-existent spree returns 404."""
    non_existent_id = str(uuid.uuid4())
    response = client.post(f"/api/v1/sprees/{non_existent_id}/view", json={"watch_duration": 10.0})
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ============================================================================
# R2: Claps Endpoints (POST/DELETE /api/v1/sprees/{id}/clap)
# ============================================================================

def test_clap_spree_authenticated_success(client: TestClient, db_session: Session):
    """Test clapping a valid spree with authentication."""
    creator = create_test_user(db_session, username="creator_clap_1")
    user = create_test_user(db_session, username="user_clap_1")
    spree = create_test_spree(db_session, creator)

    response = client.post(
        f"/api/v1/sprees/{spree.id}/clap",
        headers=auth_headers(user.id),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["clapped"] is True
    assert "clapped successfully" in data["message"].lower()

    # Direct DB verification
    clap_in_db = db_session.query(SpreeClap).filter_by(spree_id=spree.id, user_id=user.id).first()
    assert clap_in_db is not None


def test_clap_spree_idempotent_duplicate(client: TestClient, db_session: Session):
    """Test that clapping the same spree multiple times is idempotent and duplicate-safe."""
    creator = create_test_user(db_session, username="creator_clap_2")
    user = create_test_user(db_session, username="user_clap_2")
    spree = create_test_spree(db_session, creator)

    headers = auth_headers(user.id)
    first_resp = client.post(f"/api/v1/sprees/{spree.id}/clap", headers=headers)
    assert first_resp.status_code == 200

    # Second clap should succeed idempotently
    second_resp = client.post(f"/api/v1/sprees/{spree.id}/clap", headers=headers)
    assert second_resp.status_code == 200
    assert second_resp.json()["clapped"] is True

    # Ensure only a single row exists in DB
    count = db_session.query(SpreeClap).filter_by(spree_id=spree.id, user_id=user.id).count()
    assert count == 1


def test_clap_spree_unauthenticated_rejected(client: TestClient, db_session: Session):
    """Test that clapping without authentication returns 401 Unauthorized."""
    creator = create_test_user(db_session, username="creator_clap_3")
    spree = create_test_spree(db_session, creator)

    response = client.post(f"/api/v1/sprees/{spree.id}/clap")
    assert response.status_code == 401


def test_clap_spree_nonexistent_rejected(client: TestClient, db_session: Session):
    """Test that clapping a non-existent spree returns 404 Not Found."""
    user = create_test_user(db_session, username="user_clap_4")
    non_existent_id = str(uuid.uuid4())

    response = client.post(
        f"/api/v1/sprees/{non_existent_id}/clap",
        headers=auth_headers(user.id),
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_unclap_spree_authenticated_success(client: TestClient, db_session: Session):
    """Test removing a clap from a Spree."""
    creator = create_test_user(db_session, username="creator_unclap_1")
    user = create_test_user(db_session, username="user_unclap_1")
    spree = create_test_spree(db_session, creator)
    headers = auth_headers(user.id)

    # Clap first
    client.post(f"/api/v1/sprees/{spree.id}/clap", headers=headers)

    # Now unclap
    delete_resp = client.delete(f"/api/v1/sprees/{spree.id}/clap", headers=headers)
    assert delete_resp.status_code == 200
    assert delete_resp.json()["clapped"] is False

    # Verify removed in DB
    clap_in_db = db_session.query(SpreeClap).filter_by(spree_id=spree.id, user_id=user.id).first()
    assert clap_in_db is None


def test_unclap_spree_idempotent(client: TestClient, db_session: Session):
    """Test that unclapping a spree when not clapped is idempotent and returns 200."""
    creator = create_test_user(db_session, username="creator_unclap_2")
    user = create_test_user(db_session, username="user_unclap_2")
    spree = create_test_spree(db_session, creator)
    headers = auth_headers(user.id)

    # Unclap without prior clap
    response = client.delete(f"/api/v1/sprees/{spree.id}/clap", headers=headers)
    assert response.status_code == 200
    assert response.json()["clapped"] is False


def test_unclap_spree_unauthenticated_rejected(client: TestClient, db_session: Session):
    """Test that unclap without auth returns 401 Unauthorized."""
    creator = create_test_user(db_session, username="creator_unclap_3")
    spree = create_test_spree(db_session, creator)

    response = client.delete(f"/api/v1/sprees/{spree.id}/clap")
    assert response.status_code == 401


def test_unclap_spree_nonexistent_rejected(client: TestClient, db_session: Session):
    """Test that unclapping a non-existent spree returns 404."""
    user = create_test_user(db_session, username="user_unclap_4")
    non_existent_id = str(uuid.uuid4())

    response = client.delete(
        f"/api/v1/sprees/{non_existent_id}/clap",
        headers=auth_headers(user.id),
    )
    assert response.status_code == 404


# ============================================================================
# R2: Comments Endpoints (POST/GET /api/v1/sprees/{id}/comments)
# ============================================================================

def test_post_comment_authenticated_success(client: TestClient, db_session: Session):
    """Test posting a comment with authenticated user returns commenter profile info."""
    creator = create_test_user(db_session, username="creator_comm_1")
    commenter = create_test_user(
        db_session,
        username="cool_commenter",
        full_name="Cool Commenter",
        avatar_url="https://cdn.spreego.com/avatars/cool.jpg",
    )
    spree = create_test_spree(db_session, creator)

    payload = {"text": "Awesome product demo!"}
    response = client.post(
        f"/api/v1/sprees/{spree.id}/comments",
        json=payload,
        headers=auth_headers(commenter.id),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["spree_id"] == spree.id
    assert data["user_id"] == commenter.id
    assert data["text"] == "Awesome product demo!"
    assert data["parent_id"] is None
    # Commenter profile checks (both top-level and user sub-dict)
    assert data["username"] == "cool_commenter"
    assert data["avatar_url"] == "https://cdn.spreego.com/avatars/cool.jpg"
    assert data["user"]["username"] == "cool_commenter"
    assert data["user"]["avatar_url"] == "https://cdn.spreego.com/avatars/cool.jpg"


def test_post_comment_unauthenticated_rejected(client: TestClient, db_session: Session):
    """Test posting comment without authentication returns 401 Unauthorized."""
    creator = create_test_user(db_session, username="creator_comm_2")
    spree = create_test_spree(db_session, creator)

    response = client.post(f"/api/v1/sprees/{spree.id}/comments", json={"text": "Hello"})
    assert response.status_code == 401


def test_post_comment_nonexistent_spree_rejected(client: TestClient, db_session: Session):
    """Test posting comment on non-existent spree returns 404 Not Found."""
    commenter = create_test_user(db_session, username="commenter_comm_3")
    non_existent_id = str(uuid.uuid4())

    response = client.post(
        f"/api/v1/sprees/{non_existent_id}/comments",
        json={"text": "Hello"},
        headers=auth_headers(commenter.id),
    )
    assert response.status_code == 404


def test_post_comment_empty_text_rejected(client: TestClient, db_session: Session):
    """Test posting empty or whitespace comment returns 422 or 400."""
    creator = create_test_user(db_session, username="creator_comm_4")
    commenter = create_test_user(db_session, username="commenter_comm_4")
    spree = create_test_spree(db_session, creator)

    response = client.post(
        f"/api/v1/sprees/{spree.id}/comments",
        json={"text": "   "},
        headers=auth_headers(commenter.id),
    )
    assert response.status_code in (400, 422)


def test_post_nested_reply_comment_success(client: TestClient, db_session: Session):
    """Test posting a nested reply with parent_id."""
    creator = create_test_user(db_session, username="creator_reply_1")
    user1 = create_test_user(db_session, username="parent_poster")
    user2 = create_test_user(db_session, username="reply_poster")
    spree = create_test_spree(db_session, creator)

    # Post parent comment
    parent_resp = client.post(
        f"/api/v1/sprees/{spree.id}/comments",
        json={"text": "Top level feedback"},
        headers=auth_headers(user1.id),
    )
    assert parent_resp.status_code == 201
    parent_id = parent_resp.json()["id"]

    # Post reply
    reply_resp = client.post(
        f"/api/v1/sprees/{spree.id}/comments",
        json={"text": "I agree with this!", "parent_id": parent_id},
        headers=auth_headers(user2.id),
    )
    assert reply_resp.status_code == 201
    reply_data = reply_resp.json()
    assert reply_data["parent_id"] == parent_id
    assert reply_data["username"] == "reply_poster"


def test_post_nested_reply_invalid_parent_rejected(client: TestClient, db_session: Session):
    """Test posting reply with non-existent parent_id returns 404."""
    creator = create_test_user(db_session, username="creator_reply_2")
    user = create_test_user(db_session, username="reply_poster_2")
    spree = create_test_spree(db_session, creator)

    invalid_parent_id = str(uuid.uuid4())
    reply_resp = client.post(
        f"/api/v1/sprees/{spree.id}/comments",
        json={"text": "Orphan reply", "parent_id": invalid_parent_id},
        headers=auth_headers(user.id),
    )
    assert reply_resp.status_code in (400, 404)


def test_get_comments_pagination_and_profiles(client: TestClient, db_session: Session):
    """Test paginated comment list with commenter usernames and avatars."""
    creator = create_test_user(db_session, username="creator_get_comm")
    spree = create_test_spree(db_session, creator)

    user_a = create_test_user(db_session, username="alice_comm", avatar_url="https://cdn.com/alice.png")
    user_b = create_test_user(db_session, username="bob_comm", avatar_url="https://cdn.com/bob.png")
    user_c = create_test_user(db_session, username="carol_comm", avatar_url="https://cdn.com/carol.png")

    # Post 3 comments in chronological order
    client.post(f"/api/v1/sprees/{spree.id}/comments", json={"text": "Comment 1"}, headers=auth_headers(user_a.id))
    client.post(f"/api/v1/sprees/{spree.id}/comments", json={"text": "Comment 2"}, headers=auth_headers(user_b.id))
    client.post(f"/api/v1/sprees/{spree.id}/comments", json={"text": "Comment 3"}, headers=auth_headers(user_c.id))

    # Fetch all (limit=10)
    all_resp = client.get(f"/api/v1/sprees/{spree.id}/comments?limit=10")
    assert all_resp.status_code == 200
    all_comments = all_resp.json()
    assert len(all_comments) == 3
    assert all_comments[0]["username"] == "alice_comm"
    assert all_comments[0]["avatar_url"] == "https://cdn.com/alice.png"
    assert all_comments[1]["username"] == "bob_comm"
    assert all_comments[2]["username"] == "carol_comm"

    # Pagination: page=1, limit=2
    p1_resp = client.get(f"/api/v1/sprees/{spree.id}/comments?page=1&limit=2")
    assert p1_resp.status_code == 200
    p1 = p1_resp.json()
    assert len(p1) == 2
    assert p1[0]["text"] == "Comment 1"
    assert p1[1]["text"] == "Comment 2"

    # Pagination: page=2, limit=2
    p2_resp = client.get(f"/api/v1/sprees/{spree.id}/comments?page=2&limit=2")
    assert p2_resp.status_code == 200
    p2 = p2_resp.json()
    assert len(p2) == 1
    assert p2[0]["text"] == "Comment 3"

    # Pagination via skip: skip=1, limit=1
    skip_resp = client.get(f"/api/v1/sprees/{spree.id}/comments?skip=1&limit=1")
    assert skip_resp.status_code == 200
    assert len(skip_resp.json()) == 1
    assert skip_resp.json()[0]["text"] == "Comment 2"


def test_get_comments_nonexistent_spree_rejected(client: TestClient, db_session: Session):
    """Test getting comments for non-existent spree returns 404."""
    non_existent_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/sprees/{non_existent_id}/comments")
    assert response.status_code == 404


# ============================================================================
# R2: Shares Endpoints (POST /api/v1/sprees/{id}/share)
# ============================================================================

def test_record_share_anonymous_success(client: TestClient, db_session: Session):
    """Test anonymous share event increments share metrics."""
    creator = create_test_user(db_session, username="creator_share_1")
    spree = create_test_spree(db_session, creator)

    payload = {"platform": "whatsapp"}
    response = client.post(f"/api/v1/sprees/{spree.id}/share", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["spree_id"] == spree.id
    assert data["platform"] == "whatsapp"
    assert data["user_id"] is None
    assert data["share_count"] == 1


def test_record_share_authenticated_and_metric_increment(client: TestClient, db_session: Session):
    """Test authenticated share increments the share metrics count."""
    creator = create_test_user(db_session, username="creator_share_2")
    user = create_test_user(db_session, username="sharer_2")
    spree = create_test_spree(db_session, creator)

    # First share
    r1 = client.post(
        f"/api/v1/sprees/{spree.id}/share",
        json={"platform": "twitter"},
        headers=auth_headers(user.id),
    )
    assert r1.status_code == 200
    assert r1.json()["share_count"] == 1
    assert r1.json()["user_id"] == user.id

    # Second share
    r2 = client.post(
        f"/api/v1/sprees/{spree.id}/share",
        json={"platform": "telegram"},
        headers=auth_headers(user.id),
    )
    assert r2.status_code == 200
    assert r2.json()["share_count"] == 2


def test_record_share_empty_payload(client: TestClient, db_session: Session):
    """Test share event with empty payload or no body records without platform."""
    creator = create_test_user(db_session, username="creator_share_3")
    spree = create_test_spree(db_session, creator)

    response = client.post(f"/api/v1/sprees/{spree.id}/share", json={})
    assert response.status_code == 200
    data = response.json()
    assert data["platform"] is None
    assert data["share_count"] == 1

    # Also test posting with no body
    resp_no_body = client.post(f"/api/v1/sprees/{spree.id}/share")
    assert resp_no_body.status_code == 200
    assert resp_no_body.json()["platform"] is None
    assert resp_no_body.json()["share_count"] == 2


def test_record_share_nonexistent_spree(client: TestClient, db_session: Session):
    """Test sharing non-existent spree returns 404."""
    non_existent_id = str(uuid.uuid4())
    response = client.post(f"/api/v1/sprees/{non_existent_id}/share", json={"platform": "facebook"})
    assert response.status_code == 404


# ============================================================================
# R2: Saves / Bookmarks Endpoints (POST/DELETE /api/v1/sprees/{id}/save)
# ============================================================================

def test_save_spree_authenticated_success(client: TestClient, db_session: Session):
    """Test authenticated bookmark/save of a Spree."""
    creator = create_test_user(db_session, username="creator_save_1")
    user = create_test_user(db_session, username="saver_1")
    spree = create_test_spree(db_session, creator)

    response = client.post(
        f"/api/v1/sprees/{spree.id}/save",
        headers=auth_headers(user.id),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["saved"] is True
    assert "saved successfully" in data["message"].lower()

    # DB check
    saved_in_db = db_session.query(SpreeSave).filter_by(spree_id=spree.id, user_id=user.id).first()
    assert saved_in_db is not None


def test_save_spree_idempotent_duplicate(client: TestClient, db_session: Session):
    """Test saving an already-saved Spree is idempotent and duplicate-safe."""
    creator = create_test_user(db_session, username="creator_save_2")
    user = create_test_user(db_session, username="saver_2")
    spree = create_test_spree(db_session, creator)

    headers = auth_headers(user.id)
    r1 = client.post(f"/api/v1/sprees/{spree.id}/save", headers=headers)
    assert r1.status_code == 200

    r2 = client.post(f"/api/v1/sprees/{spree.id}/save", headers=headers)
    assert r2.status_code == 200
    assert r2.json()["saved"] is True

    # Single DB row
    count = db_session.query(SpreeSave).filter_by(spree_id=spree.id, user_id=user.id).count()
    assert count == 1


def test_save_spree_unauthenticated_rejected(client: TestClient, db_session: Session):
    """Test saving without auth returns 401 Unauthorized."""
    creator = create_test_user(db_session, username="creator_save_3")
    spree = create_test_spree(db_session, creator)

    response = client.post(f"/api/v1/sprees/{spree.id}/save")
    assert response.status_code == 401


def test_save_spree_nonexistent_rejected(client: TestClient, db_session: Session):
    """Test saving non-existent spree returns 404 Not Found."""
    user = create_test_user(db_session, username="saver_4")
    non_existent_id = str(uuid.uuid4())

    response = client.post(
        f"/api/v1/sprees/{non_existent_id}/save",
        headers=auth_headers(user.id),
    )
    assert response.status_code == 404


def test_unsave_spree_authenticated_success(client: TestClient, db_session: Session):
    """Test removing a saved Spree bookmark."""
    creator = create_test_user(db_session, username="creator_unsave_1")
    user = create_test_user(db_session, username="saver_5")
    spree = create_test_spree(db_session, creator)
    headers = auth_headers(user.id)

    # Save first
    client.post(f"/api/v1/sprees/{spree.id}/save", headers=headers)

    # Now unsave
    delete_resp = client.delete(f"/api/v1/sprees/{spree.id}/save", headers=headers)
    assert delete_resp.status_code == 200
    assert delete_resp.json()["saved"] is False

    # DB check
    saved_in_db = db_session.query(SpreeSave).filter_by(spree_id=spree.id, user_id=user.id).first()
    assert saved_in_db is None


def test_unsave_spree_idempotent(client: TestClient, db_session: Session):
    """Test unsaving a spree when not saved is idempotent and returns 200."""
    creator = create_test_user(db_session, username="creator_unsave_2")
    user = create_test_user(db_session, username="saver_6")
    spree = create_test_spree(db_session, creator)
    headers = auth_headers(user.id)

    response = client.delete(f"/api/v1/sprees/{spree.id}/save", headers=headers)
    assert response.status_code == 200
    assert response.json()["saved"] is False


def test_unsave_spree_unauthenticated_rejected(client: TestClient, db_session: Session):
    """Test unsaving without auth returns 401."""
    creator = create_test_user(db_session, username="creator_unsave_3")
    spree = create_test_spree(db_session, creator)

    response = client.delete(f"/api/v1/sprees/{spree.id}/save")
    assert response.status_code == 401


def test_unsave_spree_nonexistent_rejected(client: TestClient, db_session: Session):
    """Test unsaving non-existent spree returns 404."""
    user = create_test_user(db_session, username="saver_7")
    non_existent_id = str(uuid.uuid4())

    response = client.delete(
        f"/api/v1/sprees/{non_existent_id}/save",
        headers=auth_headers(user.id),
    )
    assert response.status_code == 404


# ============================================================================
# Edge Cases & Full Integration
# ============================================================================

def test_trailing_slashes_supported(client: TestClient, db_session: Session):
    """Test that endpoints with trailing slashes function identically."""
    creator = create_test_user(db_session, username="creator_trail")
    user = create_test_user(db_session, username="user_trail")
    spree = create_test_spree(db_session, creator)
    headers = auth_headers(user.id)

    # POST view/
    v_resp = client.post(f"/api/v1/sprees/{spree.id}/view/", json={"watch_duration": 5.0})
    assert v_resp.status_code == 200

    # POST clap/ & DELETE clap/
    c_resp = client.post(f"/api/v1/sprees/{spree.id}/clap/", headers=headers)
    assert c_resp.status_code == 200
    uc_resp = client.delete(f"/api/v1/sprees/{spree.id}/clap/", headers=headers)
    assert uc_resp.status_code == 200

    # POST comments/ & GET comments/
    comm_resp = client.post(
        f"/api/v1/sprees/{spree.id}/comments/",
        json={"text": "Trailing slash comment"},
        headers=headers,
    )
    assert comm_resp.status_code == 201
    list_resp = client.get(f"/api/v1/sprees/{spree.id}/comments/")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # POST share/
    s_resp = client.post(f"/api/v1/sprees/{spree.id}/share/", json={"platform": "copy_link"})
    assert s_resp.status_code == 200

    # POST save/ & DELETE save/
    sv_resp = client.post(f"/api/v1/sprees/{spree.id}/save/", headers=headers)
    assert sv_resp.status_code == 200
    usv_resp = client.delete(f"/api/v1/sprees/{spree.id}/save/", headers=headers)
    assert usv_resp.status_code == 200


def test_cascade_delete_spree_removes_all_engagement(client: TestClient, db_session: Session):
    """Test that deleting a spree removes its associated views, claps, comments, saves, and shares."""
    creator = create_test_user(db_session, username="creator_cascade")
    user = create_test_user(db_session, username="user_cascade")
    spree = create_test_spree(db_session, creator)
    headers = auth_headers(user.id)

    # Populate all engagement types
    client.post(f"/api/v1/sprees/{spree.id}/view", json={"watch_duration": 10.0})
    client.post(f"/api/v1/sprees/{spree.id}/clap", headers=headers)
    client.post(f"/api/v1/sprees/{spree.id}/comments", json={"text": "Comment"}, headers=headers)
    client.post(f"/api/v1/sprees/{spree.id}/share", json={"platform": "whatsapp"})
    client.post(f"/api/v1/sprees/{spree.id}/save", headers=headers)

    # Delete spree
    delete_resp = client.delete(f"/api/v1/sprees/{spree.id}", headers=auth_headers(creator.id))
    assert delete_resp.status_code == 200

    # Ensure engagement records are cleaned up
    assert db_session.query(SpreeView).filter_by(spree_id=spree.id).count() == 0
    assert db_session.query(SpreeClap).filter_by(spree_id=spree.id).count() == 0
    assert db_session.query(SpreeComment).filter_by(spree_id=spree.id).count() == 0
    assert db_session.query(SpreeShare).filter_by(spree_id=spree.id).count() == 0
    assert db_session.query(SpreeSave).filter_by(spree_id=spree.id).count() == 0


def test_post_comment_empty_and_whitespace_parent_id_normalizes_to_none(client: TestClient, db_session: Session):
    """Test that empty string or whitespace parent_id is sanitized to None (top-level comment)."""
    creator = create_test_user(db_session, username="creator_norm_comm")
    commenter = create_test_user(db_session, username="comm_norm")
    spree = create_test_spree(db_session, creator)
    headers = auth_headers(commenter.id)

    # Empty string parent_id
    r1 = client.post(
        f"/api/v1/sprees/{spree.id}/comments",
        json={"text": "Top level 1", "parent_id": ""},
        headers=headers,
    )
    assert r1.status_code == 201
    assert r1.json()["parent_id"] is None

    # Whitespace parent_id
    r2 = client.post(
        f"/api/v1/sprees/{spree.id}/comments",
        json={"text": "Top level 2", "parent_id": "   "},
        headers=headers,
    )
    assert r2.status_code == 201
    assert r2.json()["parent_id"] is None


def test_post_comment_cross_spree_parent_rejected(client: TestClient, db_session: Session):
    """Test that attempting to reply to a comment belonging to a different spree returns 404."""
    creator = create_test_user(db_session, username="creator_cross")
    user = create_test_user(db_session, username="user_cross")
    spree_a = create_test_spree(db_session, creator, title="Spree A")
    spree_b = create_test_spree(db_session, creator, title="Spree B")
    headers = auth_headers(user.id)

    # Comment on Spree A
    r_a = client.post(
        f"/api/v1/sprees/{spree_a.id}/comments",
        json={"text": "Comment on Spree A"},
        headers=headers,
    )
    assert r_a.status_code == 201
    comment_a_id = r_a.json()["id"]

    # Attempt to reply on Spree B using Spree A's comment id
    r_cross = client.post(
        f"/api/v1/sprees/{spree_b.id}/comments",
        json={"text": "Cross-spree reply", "parent_id": comment_a_id},
        headers=headers,
    )
    assert r_cross.status_code == 404
    assert "not found on this spree" in r_cross.json()["detail"].lower()


def test_post_comment_unicode_and_emojis(client: TestClient, db_session: Session):
    """Test posting comments containing rich emojis, composite glyphs, and non-Latin scripts."""
    creator = create_test_user(db_session, username="creator_uni")
    user = create_test_user(db_session, username="user_uni")
    spree = create_test_spree(db_session, creator)
    headers = auth_headers(user.id)

    unicode_text = "🔥🚀🎉 👨‍👩‍👧‍👦 नमस्ते உலக こんにちは Привет! Wonderful work! 💯"
    resp = client.post(
        f"/api/v1/sprees/{spree.id}/comments",
        json={"text": unicode_text},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["text"] == unicode_text

    # Verify directly from DB
    saved_comment = db_session.query(SpreeComment).filter_by(id=data["id"]).first()
    assert saved_comment is not None
    assert saved_comment.text == unicode_text


def test_post_comment_length_boundaries(client: TestClient, db_session: Session):
    """Test comment length boundary conditions: 2000 chars ok, 2001 chars rejected."""
    creator = create_test_user(db_session, username="creator_len")
    user = create_test_user(db_session, username="user_len")
    spree = create_test_spree(db_session, creator)
    headers = auth_headers(user.id)

    # 2000 chars should pass
    r_valid = client.post(
        f"/api/v1/sprees/{spree.id}/comments",
        json={"text": "a" * 2000},
        headers=headers,
    )
    assert r_valid.status_code == 201

    # 2001 chars should fail validation (422)
    r_invalid = client.post(
        f"/api/v1/sprees/{spree.id}/comments",
        json={"text": "a" * 2001},
        headers=headers,
    )
    assert r_invalid.status_code == 422


def test_record_view_validation_boundaries(client: TestClient, db_session: Session):
    """Test view recording validation rejects negative watch duration, NaN, Inf, and invalid types."""
    creator = create_test_user(db_session, username="creator_vbound")
    spree = create_test_spree(db_session, creator)

    # Negative watch duration
    r_neg = client.post(f"/api/v1/sprees/{spree.id}/view", json={"watch_duration": -5.0})
    assert r_neg.status_code == 422

    # NaN rejected
    r_nan = client.post(f"/api/v1/sprees/{spree.id}/view", json={"watch_duration": "NaN"})
    assert r_nan.status_code == 422

    # Infinity rejected
    r_inf = client.post(f"/api/v1/sprees/{spree.id}/view", json={"watch_duration": "Infinity"})
    assert r_inf.status_code == 422

    # String instead of float
    r_str = client.post(f"/api/v1/sprees/{spree.id}/view", json={"watch_duration": "not_a_number"})
    assert r_str.status_code == 422


def test_record_share_platform_sanitization_and_boundaries(client: TestClient, db_session: Session):
    """Test share platform trimming, empty string normalization, and length limits."""
    creator = create_test_user(db_session, username="creator_sbound")
    spree = create_test_spree(db_session, creator)

    # Whitespace trimmed
    r_trim = client.post(f"/api/v1/sprees/{spree.id}/share", json={"platform": "  whatsapp  "})
    assert r_trim.status_code == 200
    assert r_trim.json()["platform"] == "whatsapp"

    # Whitespace-only normalized to None
    r_empty = client.post(f"/api/v1/sprees/{spree.id}/share", json={"platform": "   "})
    assert r_empty.status_code == 200
    assert r_empty.json()["platform"] is None

    # Exceeding 64 characters rejected
    r_overflow = client.post(f"/api/v1/sprees/{spree.id}/share", json={"platform": "x" * 65})
    assert r_overflow.status_code == 422


def test_get_comments_query_boundaries(client: TestClient, db_session: Session):
    """Test comment pagination query parameters edge cases and rejection of invalid values."""
    creator = create_test_user(db_session, username="creator_qbound")
    spree = create_test_spree(db_session, creator)

    # page=0 rejected (ge=1)
    assert client.get(f"/api/v1/sprees/{spree.id}/comments?page=0").status_code == 422

    # limit=0 rejected (ge=1)
    assert client.get(f"/api/v1/sprees/{spree.id}/comments?limit=0").status_code == 422

    # limit=101 rejected (le=100)
    assert client.get(f"/api/v1/sprees/{spree.id}/comments?limit=101").status_code == 422

    # skip=-1 rejected (ge=0)
    assert client.get(f"/api/v1/sprees/{spree.id}/comments?skip=-1").status_code == 422

    # High offset returns empty list successfully
    resp = client.get(f"/api/v1/sprees/{spree.id}/comments?skip=100000")
    assert resp.status_code == 200
    assert resp.json() == []

    # High page offset returns empty list successfully
    resp_page = client.get(f"/api/v1/sprees/{spree.id}/comments?page=100000")
    assert resp_page.status_code == 200
    assert resp_page.json() == []

    # Parent ID exceeding 36 chars rejected
    r_long_parent = client.post(
        f"/api/v1/sprees/{spree.id}/comments",
        json={"text": "Hello", "parent_id": "x" * 37},
        headers=auth_headers(creator.id),
    )
    assert r_long_parent.status_code == 422


def test_cascade_delete_spree_with_nested_replies(client: TestClient, db_session: Session):
    """Test that deleting a spree with multi-level nested replies cascades without foreign key errors."""
    creator = create_test_user(db_session, username="creator_casc_nest")
    user1 = create_test_user(db_session, username="user_nest_1")
    user2 = create_test_user(db_session, username="user_nest_2")
    spree = create_test_spree(db_session, creator)

    # Create top-level comment
    r_top = client.post(
        f"/api/v1/sprees/{spree.id}/comments",
        json={"text": "Parent comment"},
        headers=auth_headers(user1.id),
    )
    parent_id = r_top.json()["id"]

    # Create reply to top-level comment
    r_reply = client.post(
        f"/api/v1/sprees/{spree.id}/comments",
        json={"text": "Child reply", "parent_id": parent_id},
        headers=auth_headers(user2.id),
    )
    reply_id = r_reply.json()["id"]

    # Also add clap and save
    client.post(f"/api/v1/sprees/{spree.id}/clap", headers=auth_headers(user1.id))
    client.post(f"/api/v1/sprees/{spree.id}/save", headers=auth_headers(user2.id))

    # Delete the spree
    del_resp = client.delete(f"/api/v1/sprees/{spree.id}", headers=auth_headers(creator.id))
    assert del_resp.status_code == 200

    # Ensure all engagement records including child and parent comments are removed
    assert db_session.query(SpreeComment).filter_by(id=reply_id).first() is None
    assert db_session.query(SpreeComment).filter_by(id=parent_id).first() is None
    assert db_session.query(SpreeClap).filter_by(spree_id=spree.id).count() == 0
    assert db_session.query(SpreeSave).filter_by(spree_id=spree.id).count() == 0


def test_comment_user_without_profile(client: TestClient, db_session: Session):
    """Test commenting and listing comments when profile is missing or self-healed.

    1) Authenticated comment posting triggers get_current_user self-healing, provisioning
       a profile with an auto-generated username ('noprofile_<id[:8]>').
    2) Direct DB comments authored by a user who truly has no Profile record are handled
       gracefully by GET /comments without 500 error (username and avatar_url return None).
    """
    creator = create_test_user(db_session, username="creator_noprof")
    spree = create_test_spree(db_session, creator)

    # 1. User created without a Profile row posts a comment
    user_no_prof = User(
        phone_number="+19998887776",
        email="noprofile@spreego.com",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user_no_prof)
    db_session.commit()
    db_session.refresh(user_no_prof)
    assert user_no_prof.profile is None

    # Post comment (auth middleware self-heals profile)
    resp = client.post(
        f"/api/v1/sprees/{spree.id}/comments",
        json={"text": "Comment from profile-less user"},
        headers=auth_headers(user_no_prof.id),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["text"] == "Comment from profile-less user"

    # Profile was self-healed by auth middleware
    db_session.refresh(user_no_prof)
    assert user_no_prof.profile is not None
    assert data["username"] == user_no_prof.profile.username
    assert data["username"].startswith("noprofile_")
    assert data["avatar_url"] is None
    assert data["user"]["id"] == user_no_prof.id
    assert data["user"]["username"] == user_no_prof.profile.username
    assert data["user"]["avatar_url"] is None

    # 2. Existing comment in DB whose author genuinely has NO profile (e.g. legacy/unhealed)
    user_truly_no_prof = User(
        phone_number="+19998887779",
        email="truly_noprofile@spreego.com",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user_truly_no_prof)
    db_session.commit()
    db_session.refresh(user_truly_no_prof)
    assert user_truly_no_prof.profile is None

    comment_truly_no_prof = SpreeComment(
        spree_id=spree.id,
        user_id=user_truly_no_prof.id,
        text="Comment from truly profile-less user",
    )
    db_session.add(comment_truly_no_prof)
    db_session.commit()

    # List comments publicly (author never authenticated, profile remains None)
    list_resp = client.get(f"/api/v1/sprees/{spree.id}/comments")
    assert list_resp.status_code == 200
    comments = list_resp.json()
    assert any(c["id"] == data["id"] for c in comments)

    unprofiled_comment = next(c for c in comments if c["id"] == comment_truly_no_prof.id)
    assert unprofiled_comment["text"] == "Comment from truly profile-less user"
    assert unprofiled_comment["username"] is None
    assert unprofiled_comment["avatar_url"] is None
    assert unprofiled_comment["user"]["id"] == user_truly_no_prof.id
    assert unprofiled_comment["user"]["username"] is None
    assert unprofiled_comment["user"]["avatar_url"] is None


def test_postgresql_ddl_compilation():
    """Verify that all 5 engagement tables compile cleanly to valid PostgreSQL DDL."""
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.schema import CreateTable

    dialect = postgresql.dialect()
    table_names = ["spree_views", "spree_claps", "spree_comments", "spree_saves", "spree_shares"]
    for table_name in table_names:
        table = Base.metadata.tables[table_name]
        ddl = str(CreateTable(table).compile(dialect=dialect))
        assert f"CREATE TABLE {table_name}" in ddl
        assert "FOREIGN KEY" in ddl


def test_concurrent_duplicate_clap_race_recovery(db_session: Session):
    """Test that EngagementRepository.add_clap recovers idempotently from IntegrityError on race collision."""
    from unittest.mock import patch
    from src.repositories.engagement_repository import EngagementRepository

    creator = create_test_user(db_session, username="creator_race_c")
    user = create_test_user(db_session, username="user_race_c")
    spree = create_test_spree(db_session, creator)

    repo = EngagementRepository(db_session)
    clap1 = repo.add_clap(spree_id=spree.id, user_id=user.id)
    assert clap1 is not None

    # Simulate race: get_clap returns None initially, triggering insert collision and IntegrityError rollback
    with patch.object(repo, "get_clap", side_effect=[None, clap1]):
        clap2 = repo.add_clap(spree_id=spree.id, user_id=user.id)
        assert clap2.id == clap1.id


def test_concurrent_duplicate_save_race_recovery(db_session: Session):
    """Test that EngagementRepository.add_save recovers idempotently from IntegrityError on race collision."""
    from unittest.mock import patch
    from src.repositories.engagement_repository import EngagementRepository

    creator = create_test_user(db_session, username="creator_race_s")
    user = create_test_user(db_session, username="user_race_s")
    spree = create_test_spree(db_session, creator)

    repo = EngagementRepository(db_session)
    save1 = repo.add_save(spree_id=spree.id, user_id=user.id)
    assert save1 is not None

    # Simulate race: get_save returns None initially, triggering insert collision and IntegrityError rollback
    with patch.object(repo, "get_save", side_effect=[None, save1]):
        save2 = repo.add_save(spree_id=spree.id, user_id=user.id)
        assert save2.id == save1.id


def test_post_comment_astral_plane_and_bidi_unicode(client: TestClient, db_session: Session):
    """Test posting comments with 4-byte UTF-8, mathematical alphanumeric symbols, and RTL Arabic/Hebrew."""
    creator = create_test_user(db_session, username="creator_bidi")
    user = create_test_user(db_session, username="user_bidi")
    spree = create_test_spree(db_session, creator)
    headers = auth_headers(user.id)

    bidi_text = "مرحبا بالعالم! שלום עולם 𝄞 𝄢 𝔄𝔅ℭ 𝔸𝔹ℂ 𝒳𝒴𝒵"
    resp = client.post(
        f"/api/v1/sprees/{spree.id}/comments",
        json={"text": bidi_text},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["text"] == bidi_text


def test_regression_all_105_baseline_tests():
    """Verify that all 105 tests across auth, users, and sprees pass without regressions."""
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_auth.py",
            "tests/test_users.py",
            "tests/test_sprees.py",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Baseline test failure:\n{result.stdout}\n{result.stderr}"
    assert "105 passed" in result.stdout, f"Expected 105 passed in output:\n{result.stdout}"


