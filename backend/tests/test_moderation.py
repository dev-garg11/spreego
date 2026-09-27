import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from src.config.security import create_access_token
from src.models.moderation import (
    Block,
    Mute,
    Report,
    ReportEntityType,
    ReportReason,
    ReportStatus,
)
from src.models.profile import Profile
from src.models.user import User


def create_test_user(
    db: Session,
    username: str = "testuser",
    email: str = None,
    phone_number: str = None,
) -> User:
    uid = str(uuid.uuid4())[:8]
    user = User(
        phone_number=phone_number or f"+9198{uid[:6]}",
        email=email or f"user_{uid}@spreego.com",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    profile = Profile(
        user_id=user.id,
        username=username or f"user_{uid}",
        full_name=f"User {username}",
    )
    db.add(profile)
    db.commit()
    db.refresh(user)
    return user


def auth_headers(user_id: str) -> dict:
    token = create_access_token(user_id=user_id)
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# R2: Reports Tests
# ============================================================================

def test_create_report_success(client: TestClient, db_session: Session):
    """Test authenticated user reporting abusive content."""
    reporter = create_test_user(db_session, username="reporter_1")
    target = create_test_user(db_session, username="target_1")

    payload = {
        "entity_id": target.id,
        "entity_type": "USER",
        "reason": "HARASSMENT",
        "description": "User is sending threatening messages in comments.",
    }

    response = client.post("/api/v1/reports", json=payload, headers=auth_headers(reporter.id))
    assert response.status_code == 201
    data = response.json()
    assert data["reporter_id"] == reporter.id
    assert data["entity_id"] == target.id
    assert data["entity_type"] == "USER"
    assert data["reason"] == "HARASSMENT"
    assert data["status"] == "PENDING"
    assert data["id"] is not None


def test_create_report_moderation_alias(client: TestClient, db_session: Session):
    """Test report creation via alias endpoint /api/v1/moderation/reports."""
    reporter = create_test_user(db_session, username="reporter_alias")
    payload = {
        "entity_id": "spree-999",
        "entity_type": "SPREE",
        "reason": "COPYRIGHT",
        "description": "Stolen video content.",
    }
    response = client.post("/api/v1/moderation/reports", json=payload, headers=auth_headers(reporter.id))
    assert response.status_code == 201
    assert response.json()["reason"] == "COPYRIGHT"


def test_create_report_invalid_reason_or_entity(client: TestClient, db_session: Session):
    """Test validation errors on invalid reason or entity type."""
    reporter = create_test_user(db_session, username="reporter_invalid")

    # Invalid reason
    res1 = client.post(
        "/api/v1/reports",
        json={"entity_id": "123", "entity_type": "SPREE", "reason": "INVALID_REASON"},
        headers=auth_headers(reporter.id),
    )
    assert res1.status_code == 422

    # Invalid entity type
    res2 = client.post(
        "/api/v1/reports",
        json={"entity_id": "123", "entity_type": "INVALID_TYPE", "reason": "SPAM"},
        headers=auth_headers(reporter.id),
    )
    assert res2.status_code == 422


# ============================================================================
# R2: User Blocking Tests
# ============================================================================

def test_block_user_success(client: TestClient, db_session: Session):
    """Test blocking another user successfully."""
    user_a = create_test_user(db_session, username="blocker_alice")
    user_b = create_test_user(db_session, username="blocked_bob")

    response = client.post(f"/api/v1/users/{user_b.id}/block", headers=auth_headers(user_a.id))
    assert response.status_code == 200
    data = response.json()
    assert data["blocker_id"] == user_a.id
    assert data["blocked_id"] == user_b.id
    assert "blocked successfully" in data["message"].lower()


def test_self_block_rejected_with_400(client: TestClient, db_session: Session):
    """Test that attempting to block oneself is strictly rejected with HTTP 400."""
    user = create_test_user(db_session, username="self_blocker")

    response = client.post(f"/api/v1/users/{user.id}/block", headers=auth_headers(user.id))
    assert response.status_code == 400
    assert "cannot block yourself" in response.json()["detail"].lower()


def test_block_nonexistent_user_returns_404(client: TestClient, db_session: Session):
    """Test blocking a nonexistent user returns 404."""
    user = create_test_user(db_session, username="block_ghost")
    response = client.post("/api/v1/users/non-existent-user-id/block", headers=auth_headers(user.id))
    assert response.status_code == 404


def test_duplicate_block_idempotency(client: TestClient, db_session: Session):
    """Test that repeating a block request is idempotent and does not error."""
    user_a = create_test_user(db_session, username="blocker_dup")
    user_b = create_test_user(db_session, username="blocked_dup")

    # First block
    res1 = client.post(f"/api/v1/users/{user_b.id}/block", headers=auth_headers(user_a.id))
    assert res1.status_code == 200

    # Second block (duplicate)
    res2 = client.post(f"/api/v1/users/{user_b.id}/block", headers=auth_headers(user_a.id))
    assert res2.status_code == 200
    assert res2.json()["blocked_id"] == user_b.id


def test_unblock_user_success(client: TestClient, db_session: Session):
    """Test unblocking a previously blocked user."""
    user_a = create_test_user(db_session, username="unblocker_a")
    user_b = create_test_user(db_session, username="unblocker_b")

    # Block first
    client.post(f"/api/v1/users/{user_b.id}/block", headers=auth_headers(user_a.id))

    # Unblock
    response = client.delete(f"/api/v1/users/{user_b.id}/block", headers=auth_headers(user_a.id))
    assert response.status_code == 200
    assert "unblocked successfully" in response.json()["message"].lower()

    # Verify blocked list is empty
    list_res = client.get("/api/v1/users/me/blocked", headers=auth_headers(user_a.id))
    assert list_res.status_code == 200
    assert list_res.json() == []


def test_unblock_idempotent_when_not_blocked(client: TestClient, db_session: Session):
    """Test unblocking a user who is not currently blocked is idempotent and returns 200."""
    user_a = create_test_user(db_session, username="unblock_not_blocked_a")
    user_b = create_test_user(db_session, username="unblock_not_blocked_b")

    response = client.delete(f"/api/v1/users/{user_b.id}/block", headers=auth_headers(user_a.id))
    assert response.status_code == 200


def test_self_unblock_rejected_with_400(client: TestClient, db_session: Session):
    """Test that self-unblock returns 400 Bad Request."""
    user = create_test_user(db_session, username="self_unblocker")
    response = client.delete(f"/api/v1/users/{user.id}/block", headers=auth_headers(user.id))
    assert response.status_code == 400


def test_get_blocked_users_list(client: TestClient, db_session: Session):
    """Test listing blocked users with profile information."""
    user_a = create_test_user(db_session, username="list_blocker")
    user_b = create_test_user(db_session, username="banned_target_1")
    user_c = create_test_user(db_session, username="banned_target_2")

    client.post(f"/api/v1/users/{user_b.id}/block", headers=auth_headers(user_a.id))
    client.post(f"/api/v1/users/{user_c.id}/block", headers=auth_headers(user_a.id))

    response = client.get("/api/v1/users/me/blocked", headers=auth_headers(user_a.id))
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    blocked_ids = [item["id"] for item in items]
    assert user_b.id in blocked_ids
    assert user_c.id in blocked_ids


# ============================================================================
# R2: User Muting Tests
# ============================================================================

def test_mute_user_success(client: TestClient, db_session: Session):
    """Test muting another user successfully."""
    user_a = create_test_user(db_session, username="muter_alice")
    user_b = create_test_user(db_session, username="muted_bob")

    response = client.post(f"/api/v1/users/{user_b.id}/mute", headers=auth_headers(user_a.id))
    assert response.status_code == 200
    data = response.json()
    assert data["muter_id"] == user_a.id
    assert data["muted_id"] == user_b.id
    assert "muted successfully" in data["message"].lower()


def test_self_mute_rejected_with_400(client: TestClient, db_session: Session):
    """Test that attempting to mute oneself is strictly rejected with HTTP 400."""
    user = create_test_user(db_session, username="self_muter")

    response = client.post(f"/api/v1/users/{user.id}/mute", headers=auth_headers(user.id))
    assert response.status_code == 400
    assert "cannot mute yourself" in response.json()["detail"].lower()


def test_mute_nonexistent_user_returns_404(client: TestClient, db_session: Session):
    """Test muting a nonexistent user returns 404."""
    user = create_test_user(db_session, username="mute_ghost")
    response = client.post("/api/v1/users/non-existent-user-id/mute", headers=auth_headers(user.id))
    assert response.status_code == 404


def test_duplicate_mute_idempotency(client: TestClient, db_session: Session):
    """Test that repeating a mute request is idempotent and does not error."""
    user_a = create_test_user(db_session, username="muter_dup")
    user_b = create_test_user(db_session, username="muted_dup")

    res1 = client.post(f"/api/v1/users/{user_b.id}/mute", headers=auth_headers(user_a.id))
    assert res1.status_code == 200

    res2 = client.post(f"/api/v1/users/{user_b.id}/mute", headers=auth_headers(user_a.id))
    assert res2.status_code == 200
    assert res2.json()["muted_id"] == user_b.id


def test_unmute_user_success(client: TestClient, db_session: Session):
    """Test unmuting a previously muted user."""
    user_a = create_test_user(db_session, username="unmuter_a")
    user_b = create_test_user(db_session, username="unmuter_b")

    client.post(f"/api/v1/users/{user_b.id}/mute", headers=auth_headers(user_a.id))

    response = client.delete(f"/api/v1/users/{user_b.id}/mute", headers=auth_headers(user_a.id))
    assert response.status_code == 200
    assert "unmuted successfully" in response.json()["message"].lower()

    # Verify muted list is empty
    list_res = client.get("/api/v1/users/me/muted", headers=auth_headers(user_a.id))
    assert list_res.status_code == 200
    assert list_res.json() == []


def test_unmute_idempotent_when_not_muted(client: TestClient, db_session: Session):
    """Test unmuting a user who is not currently muted is idempotent and returns 200."""
    user_a = create_test_user(db_session, username="unmute_not_muted_a")
    user_b = create_test_user(db_session, username="unmute_not_muted_b")

    response = client.delete(f"/api/v1/users/{user_b.id}/mute", headers=auth_headers(user_a.id))
    assert response.status_code == 200


def test_self_unmute_rejected_with_400(client: TestClient, db_session: Session):
    """Test that self-unmute returns 400 Bad Request."""
    user = create_test_user(db_session, username="self_unmuter")
    response = client.delete(f"/api/v1/users/{user.id}/mute", headers=auth_headers(user.id))
    assert response.status_code == 400


def test_get_muted_users_list(client: TestClient, db_session: Session):
    """Test listing muted users with profile information."""
    user_a = create_test_user(db_session, username="list_muter")
    user_b = create_test_user(db_session, username="muted_target_1")

    client.post(f"/api/v1/users/{user_b.id}/mute", headers=auth_headers(user_a.id))

    response = client.get("/api/v1/users/me/muted", headers=auth_headers(user_a.id))
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["id"] == user_b.id


# ============================================================================
# DB Constraints Tests (Direct Model Level)
# ============================================================================

def test_db_unique_constraint_block(db_session: Session):
    """Verify that Block model enforces uniqueness on (blocker_id, blocked_id)."""
    user_a = create_test_user(db_session, username="db_block_a")
    user_b = create_test_user(db_session, username="db_block_b")

    b1 = Block(blocker_id=user_a.id, blocked_id=user_b.id)
    db_session.add(b1)
    db_session.commit()

    b2 = Block(blocker_id=user_a.id, blocked_id=user_b.id)
    db_session.add(b2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_db_unique_constraint_mute(db_session: Session):
    """Verify that Mute model enforces uniqueness on (muter_id, muted_id)."""
    user_a = create_test_user(db_session, username="db_mute_a")
    user_b = create_test_user(db_session, username="db_mute_b")

    m1 = Mute(muter_id=user_a.id, muted_id=user_b.id)
    db_session.add(m1)
    db_session.commit()

    m2 = Mute(muter_id=user_a.id, muted_id=user_b.id)
    db_session.add(m2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ============================================================================
# Unauthenticated Access Tests
# ============================================================================

def test_moderation_unauthenticated_rejected(client: TestClient):
    """Test that all moderation endpoints require authentication (401)."""
    assert client.post("/api/v1/reports", json={}).status_code == 401
    assert client.post("/api/v1/users/123/block").status_code == 401
    assert client.delete("/api/v1/users/123/block").status_code == 401
    assert client.get("/api/v1/users/me/blocked").status_code == 401
    assert client.post("/api/v1/users/123/mute").status_code == 401
    assert client.delete("/api/v1/users/123/mute").status_code == 401
    assert client.get("/api/v1/users/me/muted").status_code == 401


# ============================================================================
# Additional Edge Case & Constraint Tests
# ============================================================================

def test_db_check_constraint_self_block(db_session: Session):
    """Verify that Block model DB check constraint rejects self-block."""
    user = create_test_user(db_session, username="db_self_block")
    b = Block(blocker_id=user.id, blocked_id=user.id)
    db_session.add(b)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_db_check_constraint_self_mute(db_session: Session):
    """Verify that Mute model DB check constraint rejects self-mute."""
    user = create_test_user(db_session, username="db_self_mute")
    m = Mute(muter_id=user.id, muted_id=user.id)
    db_session.add(m)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_report_all_reasons_and_entity_types(client: TestClient, db_session: Session):
    """Test creating reports across all valid reasons and entity types."""
    user = create_test_user(db_session, username="multi_reporter")
    for r in ReportReason:
        for e in ReportEntityType:
            payload = {
                "entity_id": f"id-{r.value}-{e.value}",
                "entity_type": e.value,
                "reason": r.value,
                "description": f"Testing {r.value} on {e.value}",
            }
            res = client.post("/api/v1/reports", json=payload, headers=auth_headers(user.id))
            assert res.status_code == 201
            assert res.json()["reason"] == r.value
            assert res.json()["entity_type"] == e.value


def test_block_and_mute_same_user_independent(client: TestClient, db_session: Session):
    """Verify user can independently block and mute the same target user."""
    user_a = create_test_user(db_session, username="dual_user_a")
    user_b = create_test_user(db_session, username="dual_user_b")

    # Block
    res_b = client.post(f"/api/v1/users/{user_b.id}/block", headers=auth_headers(user_a.id))
    assert res_b.status_code == 200

    # Mute
    res_m = client.post(f"/api/v1/users/{user_b.id}/mute", headers=auth_headers(user_a.id))
    assert res_m.status_code == 200

    # Both lists contain user_b
    blocked = client.get("/api/v1/users/me/blocked", headers=auth_headers(user_a.id)).json()
    muted = client.get("/api/v1/users/me/muted", headers=auth_headers(user_a.id)).json()
    assert any(item["id"] == user_b.id for item in blocked)
    assert any(item["id"] == user_b.id for item in muted)


def test_block_and_mute_inactive_user_returns_404(client: TestClient, db_session: Session):
    """Test that attempting to block or mute an inactive user returns 404."""
    user_a = create_test_user(db_session, username="active_user_a")
    user_b = create_test_user(db_session, username="inactive_user_b")
    user_b.is_active = False
    db_session.commit()

    assert client.post(f"/api/v1/users/{user_b.id}/block", headers=auth_headers(user_a.id)).status_code == 404
    assert client.post(f"/api/v1/users/{user_b.id}/mute", headers=auth_headers(user_a.id)).status_code == 404


def test_self_block_via_me_identifier_returns_400(client: TestClient, db_session: Session):
    """Test that attempting to block 'me' is rejected with HTTP 400."""
    user = create_test_user(db_session, username="me_blocker")
    res = client.post("/api/v1/users/me/block", headers=auth_headers(user.id))
    assert res.status_code == 400
    assert "cannot block yourself" in res.json()["detail"].lower()


def test_self_mute_via_me_identifier_returns_400(client: TestClient, db_session: Session):
    """Test that attempting to mute 'me' is rejected with HTTP 400."""
    user = create_test_user(db_session, username="me_muter")
    res = client.post("/api/v1/users/me/mute", headers=auth_headers(user.id))
    assert res.status_code == 400
    assert "cannot mute yourself" in res.json()["detail"].lower()


def test_self_unblock_via_me_identifier_returns_400(client: TestClient, db_session: Session):
    """Test that attempting to unblock 'me' is rejected with HTTP 400."""
    user = create_test_user(db_session, username="me_unblocker")
    res = client.delete("/api/v1/users/me/block", headers=auth_headers(user.id))
    assert res.status_code == 400
    assert "cannot unblock yourself" in res.json()["detail"].lower()


def test_self_unmute_via_me_identifier_returns_400(client: TestClient, db_session: Session):
    """Test that attempting to unmute 'me' is rejected with HTTP 400."""
    user = create_test_user(db_session, username="me_unmuter")
    res = client.delete("/api/v1/users/me/mute", headers=auth_headers(user.id))
    assert res.status_code == 400
    assert "cannot unmute yourself" in res.json()["detail"].lower()


def test_self_report_user_rejected_with_400(client: TestClient, db_session: Session):
    """Test that attempting to report oneself as USER is rejected with HTTP 400."""
    user = create_test_user(db_session, username="self_reporter")
    # Using own UUID
    res1 = client.post(
        "/api/v1/reports",
        json={"entity_id": user.id, "entity_type": "USER", "reason": "HARASSMENT"},
        headers=auth_headers(user.id),
    )
    assert res1.status_code == 400
    assert "cannot report yourself" in res1.json()["detail"].lower()

    # Using 'me'
    res2 = client.post(
        "/api/v1/reports",
        json={"entity_id": "me", "entity_type": "USER", "reason": "SPAM"},
        headers=auth_headers(user.id),
    )
    assert res2.status_code == 400
    assert "cannot report yourself" in res2.json()["detail"].lower()


def test_report_empty_entity_id_rejected_with_422(client: TestClient, db_session: Session):
    """Test that empty or blank entity_id is rejected by schema validation."""
    user = create_test_user(db_session, username="empty_entity_reporter")
    res = client.post(
        "/api/v1/reports",
        json={"entity_id": "", "entity_type": "SPREE", "reason": "SPAM"},
        headers=auth_headers(user.id),
    )
    assert res.status_code == 422


def test_moderation_route_aliases_and_slashes(client: TestClient, db_session: Session):
    """Test alternative route aliases mounted under /api/v1/moderation."""
    user_a = create_test_user(db_session, username="alias_user_a")
    user_b = create_test_user(db_session, username="alias_user_b")

    # Block with trailing slash under moderation prefix
    res_b = client.post(f"/api/v1/moderation/users/{user_b.id}/block/", headers=auth_headers(user_a.id))
    assert res_b.status_code == 200

    # Get blocked list via moderation alias
    res_list = client.get("/api/v1/moderation/users/me/blocked", headers=auth_headers(user_a.id))
    assert res_list.status_code == 200
    assert len(res_list.json()) == 1

    # Unblock with trailing slash under moderation prefix
    res_unb = client.delete(f"/api/v1/moderation/users/{user_b.id}/block/", headers=auth_headers(user_a.id))
    assert res_unb.status_code == 200

    # Mute with trailing slash under moderation prefix
    res_m = client.post(f"/api/v1/moderation/users/{user_b.id}/mute/", headers=auth_headers(user_a.id))
    assert res_m.status_code == 200

    # Get muted list via moderation alias
    res_mlist = client.get("/api/v1/moderation/users/me/muted", headers=auth_headers(user_a.id))
    assert res_mlist.status_code == 200
    assert len(res_mlist.json()) == 1

    # Unmute with trailing slash under moderation prefix
    res_unm = client.delete(f"/api/v1/moderation/users/{user_b.id}/mute/", headers=auth_headers(user_a.id))
    assert res_unm.status_code == 200


def test_self_actions_uppercase_me_rejected_with_400(client: TestClient, db_session: Session):
    """Test that uppercase or mixed-case 'ME'/'Me' self-block, self-mute, self-unblock, self-unmute, and self-report return 400."""
    user = create_test_user(db_session, username="case_me_user")

    # Self-block with 'ME'
    res_b = client.post("/api/v1/users/ME/block", headers=auth_headers(user.id))
    assert res_b.status_code == 400
    assert "cannot block yourself" in res_b.json()["detail"].lower()

    # Self-mute with 'Me'
    res_m = client.post("/api/v1/users/Me/mute", headers=auth_headers(user.id))
    assert res_m.status_code == 400
    assert "cannot mute yourself" in res_m.json()["detail"].lower()

    # Self-unblock with 'ME'
    res_ub = client.delete("/api/v1/users/ME/block", headers=auth_headers(user.id))
    assert res_ub.status_code == 400
    assert "cannot unblock yourself" in res_ub.json()["detail"].lower()

    # Self-unmute with 'Me'
    res_um = client.delete("/api/v1/users/Me/mute", headers=auth_headers(user.id))
    assert res_um.status_code == 400
    assert "cannot unmute yourself" in res_um.json()["detail"].lower()

    # Self-report with 'ME'
    res_rep = client.post(
        "/api/v1/reports",
        json={"entity_id": "ME", "entity_type": "USER", "reason": "SPAM"},
        headers=auth_headers(user.id),
    )
    assert res_rep.status_code == 400
    assert "cannot report yourself" in res_rep.json()["detail"].lower()


def test_unblock_inactive_blocked_user_success(client: TestClient, db_session: Session):
    """Test that a user can unblock another user who was deactivated after being blocked."""
    user_a = create_test_user(db_session, username="active_blocker_x")
    user_b = create_test_user(db_session, username="inactive_blocked_y")

    # Block user B
    res_b = client.post(f"/api/v1/users/{user_b.id}/block", headers=auth_headers(user_a.id))
    assert res_b.status_code == 200

    # User B account becomes inactive
    user_b.is_active = False
    db_session.commit()

    # User A unblocks User B
    res_unb = client.delete(f"/api/v1/users/{user_b.id}/block", headers=auth_headers(user_a.id))
    assert res_unb.status_code == 200
    assert "unblocked successfully" in res_unb.json()["message"].lower()

    # Verify blocked list is now empty
    blocked_list = client.get("/api/v1/users/me/blocked", headers=auth_headers(user_a.id)).json()
    assert not any(item["id"] == user_b.id for item in blocked_list)


def test_unmute_inactive_muted_user_success(client: TestClient, db_session: Session):
    """Test that a user can unmute another user who was deactivated after being muted."""
    user_a = create_test_user(db_session, username="active_muter_x")
    user_b = create_test_user(db_session, username="inactive_muted_y")

    # Mute user B
    res_m = client.post(f"/api/v1/users/{user_b.id}/mute", headers=auth_headers(user_a.id))
    assert res_m.status_code == 200

    # User B account becomes inactive
    user_b.is_active = False
    db_session.commit()

    # User A unmutes User B
    res_unm = client.delete(f"/api/v1/users/{user_b.id}/mute", headers=auth_headers(user_a.id))
    assert res_unm.status_code == 200
    assert "unmuted successfully" in res_unm.json()["message"].lower()

    # Verify muted list is now empty
    muted_list = client.get("/api/v1/users/me/muted", headers=auth_headers(user_a.id)).json()
    assert not any(item["id"] == user_b.id for item in muted_list)


def test_report_whitespace_only_entity_id_rejected_with_422(client: TestClient, db_session: Session):
    """Test that whitespace-only entity_id is rejected with 422 by schema validation."""
    user = create_test_user(db_session, username="ws_entity_reporter")
    res = client.post(
        "/api/v1/reports",
        json={"entity_id": "   ", "entity_type": "SPREE", "reason": "SPAM"},
        headers=auth_headers(user.id),
    )
    assert res.status_code == 422

