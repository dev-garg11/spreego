from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.config.security import create_access_token
from src.models.follow import Follow
from src.models.profile import Profile
from src.models.user import User


def create_test_user(
    db: Session,
    phone_number: str = "+1234567890",
    email: str = "test@spreego.com",
    username: str = "testuser",
    full_name: str = "Test User",
    bio: str = "Hello world bio",
    avatar_url: str = "https://example.com/avatar.png",
    is_active: bool = True,
) -> User:
    """Helper to provision a verified user with profile directly into test DB."""
    user = User(
        phone_number=phone_number,
        email=email,
        is_active=is_active,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    profile = Profile(
        user_id=user.id,
        username=username,
        full_name=full_name,
        bio=bio,
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


# ============================================================================
# R2: User & Profile Lookup (GET /api/v1/users/{id})
# ============================================================================

def test_get_user_profile_success(client: TestClient, db_session: Session):
    """Test public profile lookup for an existing user."""
    user = create_test_user(db_session, phone_number="+1111111111", email="alice@test.com", username="alice_wonder")
    response = client.get(f"/api/v1/users/{user.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user.id
    assert data["username"] == "alice_wonder"
    assert data["full_name"] == "Test User"
    assert data["bio"] == "Hello world bio"
    assert data["avatar_url"] == "https://example.com/avatar.png"
    assert data["followers_count"] == 0
    assert data["following_count"] == 0


def test_get_user_profile_non_existent(client: TestClient):
    """Test public profile lookup for non-existent user returns 404."""
    response = client.get("/api/v1/users/non-existent-user-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found."


def test_get_user_profile_inactive_user(client: TestClient, db_session: Session):
    """Test public profile lookup for inactive user returns 404."""
    user = create_test_user(db_session, phone_number="+1222222222", email="inactive@test.com", username="inactive_user", is_active=False)
    response = client.get(f"/api/v1/users/{user.id}")
    assert response.status_code == 404


# ============================================================================
# R2: Profile Updates (PATCH /api/v1/users/me)
# ============================================================================

def test_update_profile_full(client: TestClient, db_session: Session):
    """Test updating all profile details for authenticated user."""
    user = create_test_user(db_session, phone_number="+1333333333", email="bob@test.com", username="bob_original")
    headers = auth_headers(user.id)

    payload = {
        "full_name": "Bob Builder",
        "username": "bob_updated",
        "bio": "Can we fix it? Yes we can!",
        "avatar_url": "https://example.com/bob.jpg",
    }
    response = client.patch("/api/v1/users/me", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user.id
    assert data["username"] == "bob_updated"
    assert data["full_name"] == "Bob Builder"
    assert data["bio"] == "Can we fix it? Yes we can!"
    assert data["avatar_url"] == "https://example.com/bob.jpg"

    # Verify persistence in DB
    refreshed = client.get(f"/api/v1/users/{user.id}")
    assert refreshed.status_code == 200
    assert refreshed.json()["username"] == "bob_updated"


def test_update_profile_partial(client: TestClient, db_session: Session):
    """Test partial profile updates leaving unspecified fields unchanged."""
    user = create_test_user(
        db_session,
        phone_number="+1444444444",
        email="charlie@test.com",
        username="charlie_orig",
        full_name="Charlie Chaplin",
        bio="Silent actor",
        avatar_url="https://example.com/charlie.png",
    )
    headers = auth_headers(user.id)

    # Update only bio
    response = client.patch("/api/v1/users/me", json={"bio": "New silent bio"}, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["bio"] == "New silent bio"
    assert data["username"] == "charlie_orig"
    assert data["full_name"] == "Charlie Chaplin"
    assert data["avatar_url"] == "https://example.com/charlie.png"

    # Update only full_name
    response2 = client.patch("/api/v1/users/me", json={"full_name": "Sir Charlie"}, headers=headers)
    assert response2.status_code == 200
    assert response2.json()["full_name"] == "Sir Charlie"
    assert response2.json()["bio"] == "New silent bio"


def test_update_profile_same_username_allowed(client: TestClient, db_session: Session):
    """Test updating profile with the user's current username does not trigger uniqueness conflict."""
    user = create_test_user(db_session, phone_number="+1555555555", email="dave@test.com", username="dave_unique")
    headers = auth_headers(user.id)

    response = client.patch("/api/v1/users/me", json={"username": "dave_unique", "full_name": "Dave New"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["username"] == "dave_unique"
    assert response.json()["full_name"] == "Dave New"


def test_update_profile_duplicate_username_rejected(client: TestClient, db_session: Session):
    """Test updating username to an already existing username returns 400."""
    create_test_user(db_session, phone_number="+1666666666", email="eva@test.com", username="eva_star")
    user2 = create_test_user(db_session, phone_number="+1777777777", email="frank@test.com", username="frank_user")

    headers = auth_headers(user2.id)
    response = client.patch("/api/v1/users/me", json={"username": "eva_star"}, headers=headers)
    assert response.status_code == 400
    assert "Username already taken" in response.json()["detail"]


def test_update_profile_empty_username_rejected(client: TestClient, db_session: Session):
    """Test updating username to empty string is rejected."""
    user = create_test_user(db_session, phone_number="+1888888888", email="grace@test.com", username="grace_user")
    headers = auth_headers(user.id)

    response = client.patch("/api/v1/users/me", json={"username": "   "}, headers=headers)
    assert response.status_code in (400, 422)


def test_update_profile_unauthenticated(client: TestClient):
    """Test updating profile without authentication credentials returns 401."""
    response = client.patch("/api/v1/users/me", json={"full_name": "Hacker"})
    assert response.status_code == 401


# ============================================================================
# R3: Social & Follow Endpoints (POST/DELETE follow, followers/following list)
# ============================================================================

def test_follow_user_success(client: TestClient, db_session: Session):
    """Test user A follows user B and counts reflect accurately."""
    user_a = create_test_user(db_session, phone_number="+1999999991", email="a@test.com", username="user_a")
    user_b = create_test_user(db_session, phone_number="+1999999992", email="b@test.com", username="user_b")

    headers_a = auth_headers(user_a.id)
    response = client.post(f"/api/v1/users/{user_b.id}/follow", headers=headers_a)
    assert response.status_code == 200
    assert response.json()["message"] == "User followed successfully."

    # Verify user_a following count is 1, followers count is 0
    resp_a = client.get(f"/api/v1/users/{user_a.id}")
    assert resp_a.json()["following_count"] == 1
    assert resp_a.json()["followers_count"] == 0

    # Verify user_b followers count is 1, following count is 0
    resp_b = client.get(f"/api/v1/users/{user_b.id}")
    assert resp_b.json()["followers_count"] == 1
    assert resp_b.json()["following_count"] == 0


def test_follow_user_self_rejected(client: TestClient, db_session: Session):
    """Test user attempting to follow themselves returns 400 Bad Request."""
    user = create_test_user(db_session, phone_number="+1999999993", email="self@test.com", username="self_user")
    headers = auth_headers(user.id)

    response = client.post(f"/api/v1/users/{user.id}/follow", headers=headers)
    assert response.status_code == 400
    assert "cannot follow yourself" in response.json()["detail"].lower()


def test_follow_user_duplicate_rejected(client: TestClient, db_session: Session):
    """Test duplicate follow attempt returns 400 Bad Request."""
    user_a = create_test_user(db_session, phone_number="+1999999994", email="dup_a@test.com", username="dup_a")
    user_b = create_test_user(db_session, phone_number="+1999999995", email="dup_b@test.com", username="dup_b")

    headers_a = auth_headers(user_a.id)
    first_resp = client.post(f"/api/v1/users/{user_b.id}/follow", headers=headers_a)
    assert first_resp.status_code == 200

    # Second follow attempt
    second_resp = client.post(f"/api/v1/users/{user_b.id}/follow", headers=headers_a)
    assert second_resp.status_code == 400
    assert "already following" in second_resp.json()["detail"].lower()


def test_follow_non_existent_user(client: TestClient, db_session: Session):
    """Test following a non-existent user returns 404."""
    user = create_test_user(db_session, phone_number="+1999999996", email="ghost@test.com", username="ghost_hunter")
    headers = auth_headers(user.id)

    response = client.post("/api/v1/users/non-existent-user-id/follow", headers=headers)
    assert response.status_code == 404


def test_follow_unauthenticated(client: TestClient, db_session: Session):
    """Test follow endpoint without token returns 401."""
    user = create_test_user(db_session, phone_number="+1999999997", email="noauth@test.com", username="noauth_target")
    response = client.post(f"/api/v1/users/{user.id}/follow")
    assert response.status_code == 401


def test_unfollow_user_success(client: TestClient, db_session: Session):
    """Test user A unfollows user B and follow count drops back to 0."""
    user_a = create_test_user(db_session, phone_number="+1999999998", email="unf_a@test.com", username="unf_a")
    user_b = create_test_user(db_session, phone_number="+1999999999", email="unf_b@test.com", username="unf_b")

    headers_a = auth_headers(user_a.id)
    # Follow first
    client.post(f"/api/v1/users/{user_b.id}/follow", headers=headers_a)

    # Unfollow
    unf_resp = client.delete(f"/api/v1/users/{user_b.id}/follow", headers=headers_a)
    assert unf_resp.status_code == 200
    assert unf_resp.json()["message"] == "User unfollowed successfully."

    # Verify counts returned to 0
    resp_a = client.get(f"/api/v1/users/{user_a.id}")
    assert resp_a.json()["following_count"] == 0

    resp_b = client.get(f"/api/v1/users/{user_b.id}")
    assert resp_b.json()["followers_count"] == 0


def test_unfollow_not_following(client: TestClient, db_session: Session):
    """Test unfollowing someone not followed returns 400."""
    user_a = create_test_user(db_session, phone_number="+1999999981", email="unf2_a@test.com", username="unf2_a")
    user_b = create_test_user(db_session, phone_number="+1999999982", email="unf2_b@test.com", username="unf2_b")

    headers_a = auth_headers(user_a.id)
    response = client.delete(f"/api/v1/users/{user_b.id}/follow", headers=headers_a)
    assert response.status_code == 400
    assert "not following" in response.json()["detail"].lower()


def test_unfollow_self_rejected(client: TestClient, db_session: Session):
    """Test unfollowing oneself returns 400."""
    user = create_test_user(db_session, phone_number="+1999999983", email="unf_self@test.com", username="unf_self")
    headers = auth_headers(user.id)

    response = client.delete(f"/api/v1/users/{user.id}/follow", headers=headers)
    assert response.status_code == 400


def test_unfollow_unauthenticated(client: TestClient, db_session: Session):
    """Test unfollow endpoint without token returns 401."""
    user = create_test_user(db_session, phone_number="+1999999984", email="unf_noauth@test.com", username="unf_noauth")
    response = client.delete(f"/api/v1/users/{user.id}/follow")
    assert response.status_code == 401


def test_followers_list_and_pagination(client: TestClient, db_session: Session):
    """Test GET /api/v1/users/{id}/followers returns paginated list of followers."""
    target = create_test_user(db_session, phone_number="+1999999970", email="target@test.com", username="target_influencer")
    follower1 = create_test_user(db_session, phone_number="+1999999971", email="f1@test.com", username="follower_one", full_name="Follower One")
    follower2 = create_test_user(db_session, phone_number="+1999999972", email="f2@test.com", username="follower_two", full_name="Follower Two")
    follower3 = create_test_user(db_session, phone_number="+1999999973", email="f3@test.com", username="follower_three", full_name="Follower Three")

    # Follow target from 3 accounts
    client.post(f"/api/v1/users/{target.id}/follow", headers=auth_headers(follower1.id))
    client.post(f"/api/v1/users/{target.id}/follow", headers=auth_headers(follower2.id))
    client.post(f"/api/v1/users/{target.id}/follow", headers=auth_headers(follower3.id))

    # All followers
    resp = client.get(f"/api/v1/users/{target.id}/followers")
    assert resp.status_code == 200
    followers = resp.json()
    assert isinstance(followers, list)
    assert len(followers) == 3
    follower_usernames = [f["username"] for f in followers]
    assert "follower_one" in follower_usernames
    assert "follower_two" in follower_usernames
    assert "follower_three" in follower_usernames

    # Pagination: limit 1, page 1
    resp_page1 = client.get(f"/api/v1/users/{target.id}/followers?page=1&limit=1")
    assert resp_page1.status_code == 200
    data_page1 = resp_page1.json()
    assert len(data_page1) == 1

    # Pagination: limit 1, page 2
    resp_page2 = client.get(f"/api/v1/users/{target.id}/followers?page=2&limit=1")
    assert resp_page2.status_code == 200
    data_page2 = resp_page2.json()
    assert len(data_page2) == 1
    assert data_page2[0]["id"] != data_page1[0]["id"]

    # Pagination: skip=1&limit=1
    resp_skip = client.get(f"/api/v1/users/{target.id}/followers?skip=1&limit=1")
    assert resp_skip.status_code == 200
    assert resp_skip.json() == data_page2


def test_following_list_and_pagination(client: TestClient, db_session: Session):
    """Test GET /api/v1/users/{id}/following returns paginated list of followed users."""
    user = create_test_user(db_session, phone_number="+1999999960", email="following_actor@test.com", username="actor_user")
    target1 = create_test_user(db_session, phone_number="+1999999961", email="t1@test.com", username="target_one")
    target2 = create_test_user(db_session, phone_number="+1999999962", email="t2@test.com", username="target_two")

    client.post(f"/api/v1/users/{target1.id}/follow", headers=auth_headers(user.id))
    client.post(f"/api/v1/users/{target2.id}/follow", headers=auth_headers(user.id))

    resp = client.get(f"/api/v1/users/{user.id}/following")
    assert resp.status_code == 200
    following = resp.json()
    assert isinstance(following, list)
    assert len(following) == 2
    following_usernames = [f["username"] for f in following]
    assert "target_one" in following_usernames
    assert "target_two" in following_usernames

    # Pagination: limit=1
    resp_p1 = client.get(f"/api/v1/users/{user.id}/following?page=1&limit=1")
    assert resp_p1.status_code == 200
    assert len(resp_p1.json()) == 1


def test_followers_list_non_existent_user(client: TestClient):
    """Test followers list for non-existent user returns 404."""
    response = client.get("/api/v1/users/non-existent-user-id/followers")
    assert response.status_code == 404


def test_following_list_non_existent_user(client: TestClient):
    """Test following list for non-existent user returns 404."""
    response = client.get("/api/v1/users/non-existent-user-id/following")
    assert response.status_code == 404


def test_update_profile_null_username_rejected(client: TestClient, db_session: Session):
    """Test updating username to null is rejected with 400 or 422."""
    user = create_test_user(db_session, phone_number="+1888888889", email="null_user@test.com", username="null_test")
    headers = auth_headers(user.id)

    response = client.patch("/api/v1/users/me", json={"username": None}, headers=headers)
    assert response.status_code in (400, 422)


def test_follow_inactive_user_rejected(client: TestClient, db_session: Session):
    """Test attempting to follow an inactive user returns 404."""
    user_a = create_test_user(db_session, phone_number="+1999999951", email="actor_a@test.com", username="actor_a")
    inactive_user = create_test_user(db_session, phone_number="+1999999952", email="inact_t@test.com", username="inact_t", is_active=False)

    response = client.post(f"/api/v1/users/{inactive_user.id}/follow", headers=auth_headers(user_a.id))
    assert response.status_code == 404


def test_unfollow_non_existent_user(client: TestClient, db_session: Session):
    """Test unfollowing a non-existent user returns 404."""
    user = create_test_user(db_session, phone_number="+1999999953", email="unf_ghost@test.com", username="unf_ghost")
    response = client.delete("/api/v1/users/non-existent-user-id/follow", headers=auth_headers(user.id))
    assert response.status_code == 404


def test_inactive_users_excluded_from_followers_and_following(client: TestClient, db_session: Session):
    """Test that deactivated users are excluded from followers/following counts and lists."""
    target = create_test_user(db_session, phone_number="+1999999940", email="star@test.com", username="star_user")
    active_follower = create_test_user(db_session, phone_number="+1999999941", email="act_f@test.com", username="active_f")
    inactive_follower = create_test_user(db_session, phone_number="+1999999942", email="inact_f@test.com", username="inactive_f")

    # Both follow target
    client.post(f"/api/v1/users/{target.id}/follow", headers=auth_headers(active_follower.id))
    client.post(f"/api/v1/users/{target.id}/follow", headers=auth_headers(inactive_follower.id))

    # Target also follows inactive_follower
    client.post(f"/api/v1/users/{inactive_follower.id}/follow", headers=auth_headers(target.id))

    # Before deactivation: target has 2 followers, 1 following
    resp_before = client.get(f"/api/v1/users/{target.id}")
    assert resp_before.json()["followers_count"] == 2
    assert resp_before.json()["following_count"] == 1

    # Deactivate inactive_follower
    inactive_follower.is_active = False
    db_session.add(inactive_follower)
    db_session.commit()

    # After deactivation: target should have 1 follower (only active_f) and 0 following
    resp_after = client.get(f"/api/v1/users/{target.id}")
    assert resp_after.json()["followers_count"] == 1
    assert resp_after.json()["following_count"] == 0

    # Followers endpoint only returns active_f
    followers_resp = client.get(f"/api/v1/users/{target.id}/followers")
    assert followers_resp.status_code == 200
    follower_items = followers_resp.json()
    assert len(follower_items) == 1
    assert follower_items[0]["id"] == active_follower.id

    # Following endpoint returns empty list
    following_resp = client.get(f"/api/v1/users/{target.id}/following")
    assert following_resp.status_code == 200
    assert len(following_resp.json()) == 0


def test_db_constraints_enforce_unique_and_no_self_follow(db_session: Session):
    """Test that SQLite/PostgreSQL schema constraints raise IntegrityError on duplicate or self-follow."""
    from sqlalchemy.exc import IntegrityError

    u1 = create_test_user(db_session, phone_number="+1999999931", email="db1@test.com", username="db_u1")
    u2 = create_test_user(db_session, phone_number="+1999999932", email="db2@test.com", username="db_u2")

    # 1. Self-follow check constraint
    with pytest.raises(IntegrityError):
        self_follow = Follow(follower_id=u1.id, following_id=u1.id)
        db_session.add(self_follow)
        db_session.commit()
    db_session.rollback()

    # 2. Duplicate follow unique constraint
    f1 = Follow(follower_id=u1.id, following_id=u2.id)
    db_session.add(f1)
    db_session.commit()

    with pytest.raises(IntegrityError):
        f2 = Follow(follower_id=u1.id, following_id=u2.id)
        db_session.add(f2)
        db_session.commit()
    db_session.rollback()


def test_update_profile_without_existing_profile_failure_does_not_create_orphan_profile(db_session: Session):
    """Test that when a user has no profile and update fails in service, no orphan profile is left in DB."""
    create_test_user(db_session, phone_number="+1888111111", email="exist@test.com", username="existing_handle")

    user_without_profile = User(
        phone_number="+1888222222",
        email="noprof@test.com",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user_without_profile)
    db_session.commit()
    db_session.refresh(user_without_profile)

    from src.repositories.profile_repository import ProfileRepository
    from src.services.user_service import UserService
    from src.validations.user_schemas import UpdateProfileRequest

    service = UserService(db_session)
    with pytest.raises(ValueError, match="already taken"):
        service.update_profile(user_without_profile, UpdateProfileRequest(username="existing_handle"))

    prof_repo = ProfileRepository(db_session)
    assert prof_repo.get_by_user_id(user_without_profile.id) is None


def test_update_profile_without_existing_profile_success(db_session: Session):
    """Test that a user without a profile can successfully create one via UserService.update_profile."""
    user = User(
        phone_number="+1888333333",
        email="noprof_succ@test.com",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    from src.repositories.profile_repository import ProfileRepository
    from src.services.user_service import UserService
    from src.validations.user_schemas import UpdateProfileRequest

    service = UserService(db_session)
    payload = UpdateProfileRequest(username="fresh_handle", full_name="Fresh User", bio="Brand new")
    resp = service.update_profile(user, payload)
    assert resp.username == "fresh_handle"
    assert resp.full_name == "Fresh User"
    assert resp.bio == "Brand new"

    prof_repo = ProfileRepository(db_session)
    saved = prof_repo.get_by_user_id(user.id)
    assert saved is not None
    assert saved.username == "fresh_handle"


def test_update_profile_empty_json_body_noop(client: TestClient, db_session: Session):
    """Test that sending an empty JSON body {} leaves existing profile fields untouched."""
    user = create_test_user(db_session, phone_number="+1888444444", email="noop@test.com", username="noop_user", full_name="Original Name")
    headers = auth_headers(user.id)

    response = client.patch("/api/v1/users/me", json={}, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "noop_user"
    assert data["full_name"] == "Original Name"


def test_get_user_profile_user_without_profile(client: TestClient, db_session: Session):
    """Test GET /api/v1/users/{id} for user without a profile returns 200 with null profile fields."""
    user = User(
        phone_number="+1888555555",
        email="bare_user@test.com",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    response = client.get(f"/api/v1/users/{user.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user.id
    assert data["username"] is None
    assert data["full_name"] is None
    assert data["followers_count"] == 0
    assert data["following_count"] == 0


def test_concurrent_follow_race_condition_handled(db_session: Session):
    """Test that concurrent follow collision raising IntegrityError in repo is translated to ValueError."""
    from unittest.mock import patch
    from sqlalchemy.exc import IntegrityError
    from src.services.user_service import UserService

    u1 = create_test_user(db_session, phone_number="+1888666661", email="race1@test.com", username="race_u1")
    u2 = create_test_user(db_session, phone_number="+1888666662", email="race2@test.com", username="race_u2")

    service = UserService(db_session)

    with patch.object(service.follow_repo, "create", side_effect=IntegrityError("stmt", {}, Exception("orig"))):
        with pytest.raises(ValueError, match="already following"):
            service.follow_user(follower_id=u1.id, target_user_id=u2.id)


def test_concurrent_username_update_race_condition_handled(db_session: Session):
    """Test that concurrent username update collision raising IntegrityError in repo is translated to ValueError."""
    from unittest.mock import patch
    from sqlalchemy.exc import IntegrityError
    from src.services.user_service import UserService
    from src.validations.user_schemas import UpdateProfileRequest

    u1 = create_test_user(db_session, phone_number="+1888777771", email="race_up@test.com", username="race_up1")
    service = UserService(db_session)

    with patch.object(service.profile_repo, "update", side_effect=IntegrityError("stmt", {}, Exception("orig"))):
        with pytest.raises(ValueError, match="already taken"):
            service.update_profile(u1, UpdateProfileRequest(username="race_new_handle"))


def test_followers_and_following_invalid_pagination_boundaries(client: TestClient, db_session: Session):
    """Test that invalid pagination parameters (page=0, skip=-1, limit=0, limit=101) return 422."""
    target = create_test_user(db_session, phone_number="+1888888880", email="bound@test.com", username="bound_user")

    resp = client.get(f"/api/v1/users/{target.id}/followers?page=0")
    assert resp.status_code == 422

    resp = client.get(f"/api/v1/users/{target.id}/followers?skip=-1")
    assert resp.status_code == 422

    resp = client.get(f"/api/v1/users/{target.id}/followers?limit=0")
    assert resp.status_code == 422

    resp = client.get(f"/api/v1/users/{target.id}/followers?limit=101")
    assert resp.status_code == 422

    resp = client.get(f"/api/v1/users/{target.id}/following?limit=0")
    assert resp.status_code == 422


def test_unfollow_inactive_user_returns_404(client: TestClient, db_session: Session):
    """Test that attempting to unfollow an inactive user returns 404."""
    user = create_test_user(db_session, phone_number="+1888999991", email="act_unf@test.com", username="act_unf")
    target = create_test_user(db_session, phone_number="+1888999992", email="inact_unf@test.com", username="inact_unf", is_active=False)

    headers = auth_headers(user.id)
    response = client.delete(f"/api/v1/users/{target.id}/follow", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found."


def test_followers_eager_loading_with_profiles(client: TestClient, db_session: Session):
    """Test that get_followers and get_following correctly populate profiles for all returned users."""
    target = create_test_user(db_session, phone_number="+1888000001", email="t_eager@test.com", username="t_eager")
    f1 = create_test_user(db_session, phone_number="+1888000002", email="f1_eager@test.com", username="f1_eager", full_name="Follower 1")
    f2 = create_test_user(db_session, phone_number="+1888000003", email="f2_eager@test.com", username="f2_eager", full_name="Follower 2")

    client.post(f"/api/v1/users/{target.id}/follow", headers=auth_headers(f1.id))
    client.post(f"/api/v1/users/{target.id}/follow", headers=auth_headers(f2.id))
    client.post(f"/api/v1/users/{f1.id}/follow", headers=auth_headers(target.id))

    followers_resp = client.get(f"/api/v1/users/{target.id}/followers")
    assert followers_resp.status_code == 200
    followers = followers_resp.json()
    assert len(followers) == 2
    assert {item["username"] for item in followers} == {"f1_eager", "f2_eager"}
    assert {item["full_name"] for item in followers} == {"Follower 1", "Follower 2"}

    following_resp = client.get(f"/api/v1/users/{target.id}/following")
    assert following_resp.status_code == 200
    following = following_resp.json()
    assert len(following) == 1
    assert following[0]["username"] == "f1_eager"
    assert following[0]["full_name"] == "Follower 1"
