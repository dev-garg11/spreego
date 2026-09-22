import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.config.security import create_access_token
from src.models.follow import Follow
from src.models.profile import Profile
from src.models.spree import Spree, SpreeType, SpreeVisibility
from src.models.user import User


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


# ============================================================================
# R1 & R2: Spree Creation (POST /api/v1/sprees)
# ============================================================================

def test_create_spree_video_short_success(client: TestClient, db_session: Session):
    """Test creating a VIDEO_SHORT spree with all fields."""
    user = create_test_user(db_session, username="creator_1")
    headers = auth_headers(user.id)

    payload = {
        "type": "VIDEO_SHORT",
        "title": "My First Short",
        "description": "A quick vertical video clip.",
        "media_url": "https://storage.spreego.com/videos/short1.mp4",
        "thumbnail_url": "https://storage.spreego.com/thumbs/short1.jpg",
        "duration": 45.5,
        "visibility": "PUBLIC",
    }

    response = client.post("/api/v1/sprees", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["creator_id"] == user.id
    assert data["type"] == "VIDEO_SHORT"
    assert data["title"] == "My First Short"
    assert data["description"] == "A quick vertical video clip."
    assert data["media_url"] == "https://storage.spreego.com/videos/short1.mp4"
    assert data["thumbnail_url"] == "https://storage.spreego.com/thumbs/short1.jpg"
    assert data["duration"] == 45.5
    assert data["visibility"] == "PUBLIC"
    assert data["created_at"] is not None
    assert data["updated_at"] is not None


def test_create_spree_photo_and_defaults(client: TestClient, db_session: Session):
    """Test creating a PHOTO spree with default visibility and optional fields omitted."""
    user = create_test_user(db_session, username="photographer")
    headers = auth_headers(user.id)

    payload = {
        "type": "PHOTO",
        "title": "Sunset View",
        "media_url": "https://storage.spreego.com/photos/sunset.jpg",
    }

    response = client.post("/api/v1/sprees", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "PHOTO"
    assert data["title"] == "Sunset View"
    assert data["media_url"] == "https://storage.spreego.com/photos/sunset.jpg"
    assert data["visibility"] == "PUBLIC"  # Default visibility
    assert data["description"] is None
    assert data["thumbnail_url"] is None
    assert data["duration"] is None


def test_create_spree_video_long_and_series(client: TestClient, db_session: Session):
    """Test creating VIDEO_LONG and SERIES spree types."""
    user = create_test_user(db_session, username="longform_creator")
    headers = auth_headers(user.id)

    # VIDEO_LONG
    resp_long = client.post(
        "/api/v1/sprees",
        headers=headers,
        json={
            "type": "VIDEO_LONG",
            "title": "Documentary Ep 1",
            "media_url": "https://storage.spreego.com/videos/doc1.mp4",
            "duration": 1800.0,
        },
    )
    assert resp_long.status_code == 201
    assert resp_long.json()["type"] == "VIDEO_LONG"

    # SERIES
    resp_series = client.post(
        "/api/v1/sprees",
        headers=headers,
        json={
            "type": "SERIES",
            "title": "Cooking Masterclass Season 1",
            "media_url": "https://storage.spreego.com/series/season1.m3u8",
        },
    )
    assert resp_series.status_code == 201
    assert resp_series.json()["type"] == "SERIES"


def test_create_spree_derives_creator_from_token_never_body(client: TestClient, db_session: Session):
    """Test that client attempting to pass creator_id in payload cannot spoof the creator."""
    legit_user = create_test_user(db_session, username="legit_creator")
    spoofed_user = create_test_user(db_session, username="victim_user")
    headers = auth_headers(legit_user.id)

    # Attempt to spoof creator_id as spoofed_user.id
    payload = {
        "creator_id": spoofed_user.id,
        "type": "PHOTO",
        "title": "Spoof Attempt",
        "media_url": "https://example.com/spoof.jpg",
    }

    response = client.post("/api/v1/sprees", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    # Must be legit_user.id, NEVER spoofed_user.id
    assert data["creator_id"] == legit_user.id
    assert data["creator_id"] != spoofed_user.id


def test_create_spree_unauthenticated_fails(client: TestClient):
    """Test creating a spree without authentication credentials returns 401."""
    payload = {
        "type": "PHOTO",
        "title": "Unauth Photo",
        "media_url": "https://example.com/unauth.jpg",
    }
    response = client.post("/api/v1/sprees", json=payload)
    assert response.status_code == 401


def test_create_spree_validation_errors(client: TestClient, db_session: Session):
    """Test validation errors for invalid types, empty titles, and negative durations."""
    user = create_test_user(db_session, username="valid_user")
    headers = auth_headers(user.id)

    # Invalid type
    resp_bad_type = client.post(
        "/api/v1/sprees",
        headers=headers,
        json={"type": "AUDIO_PODCAST", "title": "Podcast", "media_url": "https://example.com/audio.mp3"},
    )
    assert resp_bad_type.status_code == 422

    # Empty / whitespace title
    resp_empty_title = client.post(
        "/api/v1/sprees",
        headers=headers,
        json={"type": "PHOTO", "title": "   ", "media_url": "https://example.com/img.jpg"},
    )
    assert resp_empty_title.status_code in (400, 422)

    # Empty / whitespace media_url
    resp_empty_url = client.post(
        "/api/v1/sprees",
        headers=headers,
        json={"type": "PHOTO", "title": "Valid Title", "media_url": "   "},
    )
    assert resp_empty_url.status_code in (400, 422)

    # Negative duration
    resp_neg_dur = client.post(
        "/api/v1/sprees",
        headers=headers,
        json={"type": "VIDEO_SHORT", "title": "Short", "media_url": "https://example.com/v.mp4", "duration": -5.0},
    )
    assert resp_neg_dur.status_code == 422

    # Invalid visibility
    resp_bad_vis = client.post(
        "/api/v1/sprees",
        headers=headers,
        json={"type": "PHOTO", "title": "Title", "media_url": "https://example.com/p.jpg", "visibility": "HIDDEN"},
    )
    assert resp_bad_vis.status_code == 422


# ============================================================================
# R2: Single Spree Lookup & Visibility Controls (GET /api/v1/sprees/{id})
# ============================================================================

def test_get_public_spree_by_id(client: TestClient, db_session: Session):
    """Test public lookup of a PUBLIC spree succeeds for both anonymous and authenticated users."""
    creator = create_test_user(db_session, username="pub_creator")
    headers = auth_headers(creator.id)

    create_resp = client.post(
        "/api/v1/sprees",
        headers=headers,
        json={"type": "PHOTO", "title": "Public Photo", "media_url": "https://example.com/pub.jpg", "visibility": "PUBLIC"},
    )
    spree_id = create_resp.json()["id"]

    # Anonymous user lookup
    anon_resp = client.get(f"/api/v1/sprees/{spree_id}")
    assert anon_resp.status_code == 200
    assert anon_resp.json()["id"] == spree_id
    assert anon_resp.json()["title"] == "Public Photo"

    # Authenticated user lookup
    viewer = create_test_user(db_session, username="viewer_user")
    viewer_resp = client.get(f"/api/v1/sprees/{spree_id}", headers=auth_headers(viewer.id))
    assert viewer_resp.status_code == 200
    assert viewer_resp.json()["id"] == spree_id


def test_get_spree_non_existent_returns_404(client: TestClient):
    """Test requesting non-existent spree ID returns 404."""
    response = client.get("/api/v1/sprees/non-existent-id")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_private_spree_visibility_controls(client: TestClient, db_session: Session):
    """Test visibility rules for PRIVATE spree: creator can view; unauthenticated and other users blocked."""
    creator = create_test_user(db_session, username="priv_creator")
    other_user = create_test_user(db_session, username="other_user")

    create_resp = client.post(
        "/api/v1/sprees",
        headers=auth_headers(creator.id),
        json={"type": "VIDEO_SHORT", "title": "My Private Diary", "media_url": "https://example.com/p.mp4", "visibility": "PRIVATE"},
    )
    spree_id = create_resp.json()["id"]

    # 1. Creator can access their own private spree
    creator_resp = client.get(f"/api/v1/sprees/{spree_id}", headers=auth_headers(creator.id))
    assert creator_resp.status_code == 200
    assert creator_resp.json()["id"] == spree_id

    # 2. Arbitrary unauthenticated user blocked (returns 401 Unauthorized)
    anon_resp = client.get(f"/api/v1/sprees/{spree_id}")
    assert anon_resp.status_code == 401

    # 3. Authenticated other user blocked (returns 403 Forbidden)
    other_resp = client.get(f"/api/v1/sprees/{spree_id}", headers=auth_headers(other_user.id))
    assert other_resp.status_code == 403
    assert "permission" in other_resp.json()["detail"].lower()

    # 4. Verified follower is ALSO blocked from viewing PRIVATE spree (returns 403 Forbidden)
    follower = create_test_user(db_session, username="priv_follower")
    client.post(f"/api/v1/users/{creator.id}/follow", headers=auth_headers(follower.id))
    fol_resp = client.get(f"/api/v1/sprees/{spree_id}", headers=auth_headers(follower.id))
    assert fol_resp.status_code == 403
    assert "permission" in fol_resp.json()["detail"].lower()


def test_get_followers_only_spree_visibility_controls(client: TestClient, db_session: Session):
    """Test visibility rules for FOLLOWERS_ONLY spree: creator and follower can view; non-follower blocked."""
    creator = create_test_user(db_session, username="fol_creator")
    follower = create_test_user(db_session, username="loyal_fan")
    stranger = create_test_user(db_session, username="stranger_user")

    # Make follower follow creator
    client.post(f"/api/v1/users/{creator.id}/follow", headers=auth_headers(follower.id))

    # Create FOLLOWERS_ONLY spree
    create_resp = client.post(
        "/api/v1/sprees",
        headers=auth_headers(creator.id),
        json={"type": "PHOTO", "title": "Followers Exclusive", "media_url": "https://example.com/fan.jpg", "visibility": "FOLLOWERS_ONLY"},
    )
    spree_id = create_resp.json()["id"]

    # 1. Creator can view
    creator_resp = client.get(f"/api/v1/sprees/{spree_id}", headers=auth_headers(creator.id))
    assert creator_resp.status_code == 200

    # 2. Follower can view
    follower_resp = client.get(f"/api/v1/sprees/{spree_id}", headers=auth_headers(follower.id))
    assert follower_resp.status_code == 200
    assert follower_resp.json()["id"] == spree_id

    # 3. Stranger (non-follower) blocked (403 Forbidden)
    stranger_resp = client.get(f"/api/v1/sprees/{spree_id}", headers=auth_headers(stranger.id))
    assert stranger_resp.status_code == 403
    assert "follow" in stranger_resp.json()["detail"].lower()

    # 4. Unauthenticated user blocked (401 Unauthorized)
    anon_resp = client.get(f"/api/v1/sprees/{spree_id}")
    assert anon_resp.status_code == 401


# ============================================================================
# R2: Spree Updates & Ownership Security (PATCH /api/v1/sprees/{id})
# ============================================================================

def test_update_spree_success_by_creator(client: TestClient, db_session: Session):
    """Test creator successfully updates title, description, visibility, and thumbnail."""
    creator = create_test_user(db_session, username="upd_creator")
    headers = auth_headers(creator.id)

    create_resp = client.post(
        "/api/v1/sprees",
        headers=headers,
        json={"type": "VIDEO_SHORT", "title": "Original Title", "media_url": "https://example.com/v.mp4"},
    )
    spree_id = create_resp.json()["id"]

    update_payload = {
        "title": "Updated Short Title",
        "description": "Now with detailed description.",
        "visibility": "PRIVATE",
        "thumbnail_url": "https://example.com/thumb_updated.jpg",
    }

    patch_resp = client.patch(f"/api/v1/sprees/{spree_id}", headers=headers, json=update_payload)
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["title"] == "Updated Short Title"
    assert data["description"] == "Now with detailed description."
    assert data["visibility"] == "PRIVATE"
    assert data["thumbnail_url"] == "https://example.com/thumb_updated.jpg"

    # Verify persistence
    get_resp = client.get(f"/api/v1/sprees/{spree_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "Updated Short Title"


def test_update_spree_non_creator_forbidden(client: TestClient, db_session: Session):
    """Test that a non-creator attempting to update a spree receives 403 Forbidden."""
    creator = create_test_user(db_session, username="owner_user")
    attacker = create_test_user(db_session, username="hacker_user")

    create_resp = client.post(
        "/api/v1/sprees",
        headers=auth_headers(creator.id),
        json={"type": "PHOTO", "title": "Original Photo", "media_url": "https://example.com/photo.jpg"},
    )
    spree_id = create_resp.json()["id"]

    # Attacker tries to modify creator's spree
    patch_resp = client.patch(
        f"/api/v1/sprees/{spree_id}",
        headers=auth_headers(attacker.id),
        json={"title": "Hacked Title"},
    )
    assert patch_resp.status_code == 403
    assert "permission" in patch_resp.json()["detail"].lower()

    # Verify original title was NOT changed
    check_resp = client.get(f"/api/v1/sprees/{spree_id}")
    assert check_resp.json()["title"] == "Original Photo"


def test_update_spree_unauthenticated_fails(client: TestClient, db_session: Session):
    """Test updating a spree without token returns 401."""
    creator = create_test_user(db_session, username="owner2")
    create_resp = client.post(
        "/api/v1/sprees",
        headers=auth_headers(creator.id),
        json={"type": "PHOTO", "title": "My Photo", "media_url": "https://example.com/p.jpg"},
    )
    spree_id = create_resp.json()["id"]

    patch_resp = client.patch(f"/api/v1/sprees/{spree_id}", json={"title": "Anon Update"})
    assert patch_resp.status_code == 401


def test_update_spree_non_existent_returns_404(client: TestClient, db_session: Session):
    """Test updating a non-existent spree returns 404."""
    user = create_test_user(db_session, username="user_x")
    patch_resp = client.patch(
        "/api/v1/sprees/non-existent-id",
        headers=auth_headers(user.id),
        json={"title": "Does Not Matter"},
    )
    assert patch_resp.status_code == 404


def test_update_spree_empty_title_rejected(client: TestClient, db_session: Session):
    """Test updating title to empty string or whitespace is rejected."""
    creator = create_test_user(db_session, username="creator_empty")
    headers = auth_headers(creator.id)

    create_resp = client.post(
        "/api/v1/sprees",
        headers=headers,
        json={"type": "PHOTO", "title": "Valid Title", "media_url": "https://example.com/p.jpg"},
    )
    spree_id = create_resp.json()["id"]

    patch_resp = client.patch(
        f"/api/v1/sprees/{spree_id}",
        headers=headers,
        json={"title": "   "},
    )
    assert patch_resp.status_code in (400, 422)


def test_update_spree_empty_body_noop(client: TestClient, db_session: Session):
    """Test sending empty JSON body {} leaves existing spree fields unchanged."""
    creator = create_test_user(db_session, username="creator_noop")
    headers = auth_headers(creator.id)

    create_resp = client.post(
        "/api/v1/sprees",
        headers=headers,
        json={"type": "PHOTO", "title": "Stay Same", "media_url": "https://example.com/p.jpg"},
    )
    spree_id = create_resp.json()["id"]

    patch_resp = client.patch(f"/api/v1/sprees/{spree_id}", headers=headers, json={})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["title"] == "Stay Same"


# ============================================================================
# R2: Spree Deletion & Ownership Security (DELETE /api/v1/sprees/{id})
# ============================================================================

def test_delete_spree_success_by_creator(client: TestClient, db_session: Session):
    """Test creator successfully deletes their own Spree."""
    creator = create_test_user(db_session, username="del_creator")
    headers = auth_headers(creator.id)

    create_resp = client.post(
        "/api/v1/sprees",
        headers=headers,
        json={"type": "PHOTO", "title": "To Be Deleted", "media_url": "https://example.com/del.jpg"},
    )
    spree_id = create_resp.json()["id"]

    del_resp = client.delete(f"/api/v1/sprees/{spree_id}", headers=headers)
    assert del_resp.status_code == 200
    assert "deleted" in del_resp.json()["message"].lower()

    # Subsequent lookup returns 404
    get_resp = client.get(f"/api/v1/sprees/{spree_id}")
    assert get_resp.status_code == 404


def test_delete_spree_non_creator_forbidden(client: TestClient, db_session: Session):
    """Test that a non-creator attempting to delete a spree receives 403 Forbidden."""
    creator = create_test_user(db_session, username="del_owner")
    attacker = create_test_user(db_session, username="del_attacker")

    create_resp = client.post(
        "/api/v1/sprees",
        headers=auth_headers(creator.id),
        json={"type": "VIDEO_LONG", "title": "Protected Spree", "media_url": "https://example.com/long.mp4"},
    )
    spree_id = create_resp.json()["id"]

    # Attacker tries to delete creator's spree
    del_resp = client.delete(f"/api/v1/sprees/{spree_id}", headers=auth_headers(attacker.id))
    assert del_resp.status_code == 403
    assert "permission" in del_resp.json()["detail"].lower()

    # Spree should still exist
    check_resp = client.get(f"/api/v1/sprees/{spree_id}")
    assert check_resp.status_code == 200


def test_delete_spree_unauthenticated_fails(client: TestClient, db_session: Session):
    """Test deleting a spree without token returns 401."""
    creator = create_test_user(db_session, username="del_owner2")
    create_resp = client.post(
        "/api/v1/sprees",
        headers=auth_headers(creator.id),
        json={"type": "PHOTO", "title": "Photo", "media_url": "https://example.com/p.jpg"},
    )
    spree_id = create_resp.json()["id"]

    del_resp = client.delete(f"/api/v1/sprees/{spree_id}")
    assert del_resp.status_code == 401


def test_delete_spree_non_existent_returns_404(client: TestClient, db_session: Session):
    """Test deleting a non-existent spree returns 404."""
    user = create_test_user(db_session, username="del_user_x")
    del_resp = client.delete("/api/v1/sprees/non-existent-id", headers=auth_headers(user.id))
    assert del_resp.status_code == 404


# ============================================================================
# R2: Paginated Listing & Filtering by Type (GET /api/v1/sprees)
# ============================================================================

def test_list_sprees_public_feed_and_type_filtering(client: TestClient, db_session: Session):
    """Test listing public sprees and filtering by type."""
    creator = create_test_user(db_session, username="feed_creator")
    headers = auth_headers(creator.id)

    # Create 2 VIDEO_SHORT, 1 PHOTO, 1 SERIES, and 1 PRIVATE VIDEO_SHORT
    client.post("/api/v1/sprees", headers=headers, json={"type": "VIDEO_SHORT", "title": "Short 1", "media_url": "https://ex.com/s1.mp4"})
    client.post("/api/v1/sprees", headers=headers, json={"type": "VIDEO_SHORT", "title": "Short 2", "media_url": "https://ex.com/s2.mp4"})
    client.post("/api/v1/sprees", headers=headers, json={"type": "PHOTO", "title": "Photo 1", "media_url": "https://ex.com/p1.jpg"})
    client.post("/api/v1/sprees", headers=headers, json={"type": "SERIES", "title": "Series 1", "media_url": "https://ex.com/se1.m3u8"})
    # Private spree (must be excluded from public feed)
    client.post("/api/v1/sprees", headers=headers, json={"type": "VIDEO_SHORT", "title": "Secret Short", "media_url": "https://ex.com/sec.mp4", "visibility": "PRIVATE"})

    # 1. Unfiltered public list: should return exactly the 4 public sprees (no private)
    feed_resp = client.get("/api/v1/sprees")
    assert feed_resp.status_code == 200
    feed = feed_resp.json()
    assert len(feed) == 4
    titles = [s["title"] for s in feed]
    assert "Secret Short" not in titles
    assert "Short 1" in titles
    assert "Short 2" in titles
    assert "Photo 1" in titles
    assert "Series 1" in titles

    # 2. Filter by type=VIDEO_SHORT: should return only the 2 public VIDEO_SHORT sprees
    short_resp = client.get("/api/v1/sprees?type=VIDEO_SHORT")
    assert short_resp.status_code == 200
    short_feed = short_resp.json()
    assert len(short_feed) == 2
    assert all(s["type"] == "VIDEO_SHORT" for s in short_feed)

    # 3. Filter by type=PHOTO
    photo_resp = client.get("/api/v1/sprees?type=PHOTO")
    assert photo_resp.status_code == 200
    photo_feed = photo_resp.json()
    assert len(photo_feed) == 1
    assert photo_feed[0]["type"] == "PHOTO"
    assert photo_feed[0]["title"] == "Photo 1"

    # 4. Filter by type=SERIES
    series_resp = client.get("/api/v1/sprees?type=SERIES")
    assert series_resp.status_code == 200
    series_feed = series_resp.json()
    assert len(series_feed) == 1
    assert series_feed[0]["type"] == "SERIES"

    # 5. Filter by type=VIDEO_LONG (0 matching)
    long_resp = client.get("/api/v1/sprees?type=VIDEO_LONG")
    assert long_resp.status_code == 200
    assert len(long_resp.json()) == 0


def test_list_sprees_pagination(client: TestClient, db_session: Session):
    """Test pagination using page/skip/limit parameters on GET /api/v1/sprees."""
    creator = create_test_user(db_session, username="page_creator")
    headers = auth_headers(creator.id)

    # Create 5 public sprees
    for i in range(1, 6):
        client.post(
            "/api/v1/sprees",
            headers=headers,
            json={"type": "PHOTO", "title": f"Item {i}", "media_url": f"https://ex.com/{i}.jpg"},
        )

    # Page 1, limit 2
    resp_p1 = client.get("/api/v1/sprees?page=1&limit=2")
    assert resp_p1.status_code == 200
    data_p1 = resp_p1.json()
    assert len(data_p1) == 2

    # Page 2, limit 2
    resp_p2 = client.get("/api/v1/sprees?page=2&limit=2")
    assert resp_p2.status_code == 200
    data_p2 = resp_p2.json()
    assert len(data_p2) == 2
    assert data_p2[0]["id"] != data_p1[0]["id"]

    # Offset pagination with skip=2&limit=2
    resp_skip = client.get("/api/v1/sprees?skip=2&limit=2")
    assert resp_skip.status_code == 200
    assert resp_skip.json() == data_p2

    # Boundary validation: page=0, skip=-1, limit=0, limit=101
    assert client.get("/api/v1/sprees?page=0").status_code == 422
    assert client.get("/api/v1/sprees?skip=-1").status_code == 422
    assert client.get("/api/v1/sprees?limit=0").status_code == 422
    assert client.get("/api/v1/sprees?limit=101").status_code == 422


def test_user_deletion_cascade_deletes_sprees(db_session: Session):
    """Test that deleting a User cascades and deletes all their Sprees from DB."""
    user = create_test_user(db_session, username="cascade_user")
    spree1 = Spree(
        creator_id=user.id,
        type=SpreeType.PHOTO,
        title="Spree 1",
        media_url="https://ex.com/1.jpg",
    )
    spree2 = Spree(
        creator_id=user.id,
        type=SpreeType.VIDEO_SHORT,
        title="Spree 2",
        media_url="https://ex.com/2.mp4",
    )
    db_session.add_all([spree1, spree2])
    db_session.commit()

    assert db_session.query(Spree).filter(Spree.creator_id == user.id).count() == 2

    # Delete user
    db_session.delete(user)
    db_session.commit()

    # Sprees should be cascade deleted
    assert db_session.query(Spree).filter(Spree.creator_id == user.id).count() == 0


# ============================================================================
# Advanced Edge Cases & Robustness
# ============================================================================

def test_update_spree_null_required_fields_rejected(client: TestClient, db_session: Session):
    """Test setting required fields (title, media_url, visibility) to null returns 400/422, never 500."""
    creator = create_test_user(db_session, username="null_tester")
    headers = auth_headers(creator.id)

    create_resp = client.post(
        "/api/v1/sprees",
        headers=headers,
        json={"type": "PHOTO", "title": "Robust Title", "media_url": "https://example.com/r.jpg"},
    )
    spree_id = create_resp.json()["id"]

    # 1. Null title
    resp_null_title = client.patch(
        f"/api/v1/sprees/{spree_id}",
        headers=headers,
        json={"title": None},
    )
    assert resp_null_title.status_code in (400, 422)

    # 2. Null media_url
    resp_null_url = client.patch(
        f"/api/v1/sprees/{spree_id}",
        headers=headers,
        json={"media_url": None},
    )
    assert resp_null_url.status_code in (400, 422)

    # 3. Null visibility
    resp_null_vis = client.patch(
        f"/api/v1/sprees/{spree_id}",
        headers=headers,
        json={"visibility": None},
    )
    assert resp_null_vis.status_code in (400, 422)

    # Original values intact
    check_resp = client.get(f"/api/v1/sprees/{spree_id}")
    assert check_resp.status_code == 200
    assert check_resp.json()["title"] == "Robust Title"
    assert check_resp.json()["media_url"] == "https://example.com/r.jpg"


def test_followers_only_unfollow_revokes_access(client: TestClient, db_session: Session):
    """Test that unfollowing a creator immediately revokes access to FOLLOWERS_ONLY sprees."""
    creator = create_test_user(db_session, username="creator_unfol")
    viewer = create_test_user(db_session, username="viewer_unfol")

    create_resp = client.post(
        "/api/v1/sprees",
        headers=auth_headers(creator.id),
        json={
            "type": "PHOTO",
            "title": "Exclusive Club",
            "media_url": "https://example.com/club.jpg",
            "visibility": "FOLLOWERS_ONLY",
        },
    )
    spree_id = create_resp.json()["id"]

    # Step 1: Follow creator
    follow_resp = client.post(f"/api/v1/users/{creator.id}/follow", headers=auth_headers(viewer.id))
    assert follow_resp.status_code == 200

    # Step 2: Viewer can access while following
    view_resp = client.get(f"/api/v1/sprees/{spree_id}", headers=auth_headers(viewer.id))
    assert view_resp.status_code == 200
    assert view_resp.json()["id"] == spree_id

    # Step 3: Unfollow creator
    unfollow_resp = client.delete(f"/api/v1/users/{creator.id}/follow", headers=auth_headers(viewer.id))
    assert unfollow_resp.status_code == 200

    # Step 4: Access is now blocked (403 Forbidden)
    blocked_resp = client.get(f"/api/v1/sprees/{spree_id}", headers=auth_headers(viewer.id))
    assert blocked_resp.status_code == 403
    assert "follow" in blocked_resp.json()["detail"].lower()


def test_deactivated_creator_sprees_hidden_from_public_feed_and_lookup(
    client: TestClient,
    db_session: Session,
):
    """Test that deactivating a creator hides their sprees from public feed and lookup."""
    creator = create_test_user(db_session, username="deact_user")
    headers = auth_headers(creator.id)

    create_resp = client.post(
        "/api/v1/sprees",
        headers=headers,
        json={"type": "PHOTO", "title": "Ghost Spree", "media_url": "https://example.com/g.jpg"},
    )
    spree_id = create_resp.json()["id"]

    # Spree is in public feed
    feed_before = client.get("/api/v1/sprees").json()
    assert any(s["id"] == spree_id for s in feed_before)

    # Deactivate creator
    creator.is_active = False
    db_session.add(creator)
    db_session.commit()

    # Spree disappears from public feed
    feed_after = client.get("/api/v1/sprees").json()
    assert not any(s["id"] == spree_id for s in feed_after)

    # Direct lookup returns 404
    get_resp = client.get(f"/api/v1/sprees/{spree_id}")
    assert get_resp.status_code == 404


def test_visibility_transition_public_to_private_and_back(
    client: TestClient,
    db_session: Session,
):
    """Test switching visibility from PUBLIC -> PRIVATE -> PUBLIC transitions access permissions correctly."""
    creator = create_test_user(db_session, username="vis_trans_user")
    stranger = create_test_user(db_session, username="vis_stranger")
    headers = auth_headers(creator.id)

    create_resp = client.post(
        "/api/v1/sprees",
        headers=headers,
        json={"type": "PHOTO", "title": "Flip Visibility", "media_url": "https://example.com/flip.jpg", "visibility": "PUBLIC"},
    )
    spree_id = create_resp.json()["id"]

    # 1. Public: anyone can view
    assert client.get(f"/api/v1/sprees/{spree_id}").status_code == 200

    # 2. Patch to PRIVATE
    patch_priv = client.patch(
        f"/api/v1/sprees/{spree_id}",
        headers=headers,
        json={"visibility": "PRIVATE"},
    )
    assert patch_priv.status_code == 200
    assert patch_priv.json()["visibility"] == "PRIVATE"

    # Now unauthenticated is 401, stranger is 403, creator is 200
    assert client.get(f"/api/v1/sprees/{spree_id}").status_code == 401
    assert client.get(f"/api/v1/sprees/{spree_id}", headers=auth_headers(stranger.id)).status_code == 403
    assert client.get(f"/api/v1/sprees/{spree_id}", headers=headers).status_code == 200

    # 3. Patch back to PUBLIC
    patch_pub = client.patch(
        f"/api/v1/sprees/{spree_id}",
        headers=headers,
        json={"visibility": "PUBLIC"},
    )
    assert patch_pub.status_code == 200
    assert patch_pub.json()["visibility"] == "PUBLIC"

    # Anyone can view again
    assert client.get(f"/api/v1/sprees/{spree_id}").status_code == 200


def test_update_spree_clears_optional_fields(client: TestClient, db_session: Session):
    """Test updating description and thumbnail_url to empty string clears them to None."""
    creator = create_test_user(db_session, username="clear_fields_user")
    headers = auth_headers(creator.id)

    create_resp = client.post(
        "/api/v1/sprees",
        headers=headers,
        json={
            "type": "VIDEO_SHORT",
            "title": "With Thumbs",
            "media_url": "https://example.com/v.mp4",
            "description": "Initial description",
            "thumbnail_url": "https://example.com/thumb.jpg",
        },
    )
    spree_id = create_resp.json()["id"]
    assert create_resp.json()["description"] == "Initial description"
    assert create_resp.json()["thumbnail_url"] == "https://example.com/thumb.jpg"

    # Clear description and thumbnail
    patch_resp = client.patch(
        f"/api/v1/sprees/{spree_id}",
        headers=headers,
        json={"description": "   ", "thumbnail_url": "   "},
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["description"] is None
    assert data["thumbnail_url"] is None


def test_get_spree_with_invalid_bearer_token_returns_401(client: TestClient, db_session: Session):
    """Test lookup of a public spree with an invalid bearer token returns 401 Unauthorized."""
    creator = create_test_user(db_session, username="token_test_user")
    create_resp = client.post(
        "/api/v1/sprees",
        headers=auth_headers(creator.id),
        json={"type": "PHOTO", "title": "Token Test", "media_url": "https://example.com/p.jpg"},
    )
    spree_id = create_resp.json()["id"]

    resp = client.get(
        f"/api/v1/sprees/{spree_id}",
        headers={"Authorization": "Bearer totally_invalid_jwt_garbage"},
    )
    assert resp.status_code == 401


def test_list_sprees_followers_only_excluded_from_public_feed(client: TestClient, db_session: Session):
    """Test that FOLLOWERS_ONLY sprees are strictly excluded from the public feed."""
    creator = create_test_user(db_session, username="feed_fol_creator")
    headers = auth_headers(creator.id)

    # 1 Public, 1 Followers-Only
    client.post(
        "/api/v1/sprees",
        headers=headers,
        json={"type": "PHOTO", "title": "Public Photo Feed", "media_url": "https://ex.com/pub1.jpg", "visibility": "PUBLIC"},
    )
    client.post(
        "/api/v1/sprees",
        headers=headers,
        json={"type": "PHOTO", "title": "Members Only Photo", "media_url": "https://ex.com/mem1.jpg", "visibility": "FOLLOWERS_ONLY"},
    )

    feed_resp = client.get("/api/v1/sprees")
    assert feed_resp.status_code == 200
    feed = feed_resp.json()
    titles = [s["title"] for s in feed]
    assert "Public Photo Feed" in titles
    assert "Members Only Photo" not in titles


def test_update_spree_media_url_and_duration(client: TestClient, db_session: Session):
    """Test updating media_url and duration, and clearing duration by setting to null."""
    creator = create_test_user(db_session, username="media_updater")
    headers = auth_headers(creator.id)

    create_resp = client.post(
        "/api/v1/sprees",
        headers=headers,
        json={
            "type": "VIDEO_SHORT",
            "title": "Video to Update",
            "media_url": "https://ex.com/original.mp4",
            "duration": 30.0,
        },
    )
    spree_id = create_resp.json()["id"]

    # Update media_url and duration
    patch_resp = client.patch(
        f"/api/v1/sprees/{spree_id}",
        headers=headers,
        json={
            "media_url": "https://ex.com/updated.mp4",
            "duration": 45.0,
        },
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["media_url"] == "https://ex.com/updated.mp4"
    assert data["duration"] == 45.0

    # Clear duration to null
    patch_clear = client.patch(
        f"/api/v1/sprees/{spree_id}",
        headers=headers,
        json={"duration": None},
    )
    assert patch_clear.status_code == 200
    assert patch_clear.json()["duration"] is None


def test_update_spree_tamper_protected_fields_ignored(client: TestClient, db_session: Session):
    """Test attempting to overwrite protected fields (id, creator_id) in patch body is safely ignored."""
    creator = create_test_user(db_session, username="tamper_creator")
    attacker = create_test_user(db_session, username="tamper_attacker")
    headers = auth_headers(creator.id)

    create_resp = client.post(
        "/api/v1/sprees",
        headers=headers,
        json={"type": "PHOTO", "title": "Tamper Test", "media_url": "https://ex.com/t.jpg"},
    )
    original_id = create_resp.json()["id"]
    original_creator_id = create_resp.json()["creator_id"]

    # Attempt to reassign creator_id, id, and type
    patch_resp = client.patch(
        f"/api/v1/sprees/{original_id}",
        headers=headers,
        json={
            "title": "Renamed Safely",
            "creator_id": attacker.id,
            "id": "completely-fake-id",
            "type": "SERIES",
        },
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["id"] == original_id
    assert data["creator_id"] == original_creator_id
    assert data["type"] == "PHOTO"
    assert data["title"] == "Renamed Safely"


def test_list_sprees_invalid_type_filter_returns_422(client: TestClient):
    """Test passing invalid enum value in ?type query parameter returns HTTP 422."""
    resp = client.get("/api/v1/sprees?type=NON_EXISTENT_TYPE")
    assert resp.status_code == 422


def test_spree_routes_trailing_slash_support(client: TestClient, db_session: Session):
    """Test that trailing slashes on all spree endpoints are supported without 307 redirects."""
    creator = create_test_user(db_session, username="slash_user")
    headers = auth_headers(creator.id)

    # POST with trailing slash
    create_resp = client.post(
        "/api/v1/sprees/",
        headers=headers,
        json={"type": "PHOTO", "title": "Slash Photo", "media_url": "https://ex.com/slash.jpg"},
    )
    assert create_resp.status_code == 201
    spree_id = create_resp.json()["id"]

    # GET list with trailing slash
    list_resp = client.get("/api/v1/sprees/")
    assert list_resp.status_code == 200

    # GET detail with trailing slash
    detail_resp = client.get(f"/api/v1/sprees/{spree_id}/")
    assert detail_resp.status_code == 200

    # PATCH with trailing slash
    patch_resp = client.patch(
        f"/api/v1/sprees/{spree_id}/",
        headers=headers,
        json={"title": "Updated Slash Photo"},
    )
    assert patch_resp.status_code == 200

    # DELETE with trailing slash
    del_resp = client.delete(f"/api/v1/sprees/{spree_id}/", headers=headers)
    assert del_resp.status_code == 200


def test_create_spree_inactive_user_token_returns_401(client: TestClient, db_session: Session):
    """Test that an inactive user attempting to create a spree is rejected with 401 Unauthorized."""
    user = create_test_user(db_session, username="inactive_creator", is_active=False)
    headers = auth_headers(user.id)

    resp = client.post(
        "/api/v1/sprees",
        headers=headers,
        json={"type": "PHOTO", "title": "Inactive Attempt", "media_url": "https://ex.com/inact.jpg"},
    )
    assert resp.status_code == 401



