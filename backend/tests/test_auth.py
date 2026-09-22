import re
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.config.security import create_access_token, decode_token, TokenInvalidError
from src.models.otp import OTPCode
from src.models.profile import Profile
from src.models.user import User
from src.models.user_session import UserSession


def test_send_otp_success_phone(client: TestClient, capsys: pytest.CaptureFixture):
    """Test POST /auth/send-otp with phone number and verify console output."""
    response = client.post("/auth/send-otp", json={"phone_number": "+1234567890"})
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "OTP sent successfully."
    assert data["identifier"] == "+1234567890"

    # Verify mock OTP was printed to console/stdout
    captured = capsys.readouterr()
    assert "[MOCK OTP SERVICE] OTP for +1234567890:" in captured.out


def test_send_otp_success_email(client: TestClient, capsys: pytest.CaptureFixture):
    """Test POST /auth/send-otp with email identifier."""
    response = client.post("/auth/send-otp", json={"email": "shopper@spreego.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["identifier"] == "shopper@spreego.com"

    captured = capsys.readouterr()
    assert "[MOCK OTP SERVICE] OTP for shopper@spreego.com:" in captured.out


def test_send_otp_missing_identifier(client: TestClient):
    """Test POST /auth/send-otp with missing payload."""
    response = client.post("/auth/send-otp", json={})
    assert response.status_code == 422


def test_verify_otp_success_and_user_creation(client: TestClient, db_session: Session):
    """Test POST /auth/verify-otp creates new user and returns JWT access & refresh tokens."""
    phone = "+1987654321"
    send_resp = client.post("/auth/send-otp", json={"phone_number": phone})
    assert send_resp.status_code == 200

    # Retrieve generated OTP from DB
    otp_record = db_session.query(OTPCode).filter(OTPCode.identifier == phone).first()
    assert otp_record is not None
    otp_code = otp_record.otp_code

    # Verify OTP
    verify_resp = client.post("/auth/verify-otp", json={
        "phone_number": phone,
        "otp_code": otp_code,
    })
    assert verify_resp.status_code == 200
    data = verify_resp.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0

    user = data["user"]
    assert user is not None
    assert user["phone_number"] == phone
    assert user["is_verified"] is True
    assert user["is_active"] is True
    assert "profile" in user
    assert user["profile"] is not None


def test_verify_otp_wrong_code(client: TestClient):
    """Test POST /auth/verify-otp with incorrect OTP code."""
    phone = "+1555444333"
    client.post("/auth/send-otp", json={"phone_number": phone})

    verify_resp = client.post("/auth/verify-otp", json={
        "phone_number": phone,
        "otp_code": "000000",
    })
    assert verify_resp.status_code == 400
    assert "Invalid OTP code" in verify_resp.json()["detail"]


def test_verify_otp_expired_code(client: TestClient, db_session: Session):
    """Test POST /auth/verify-otp with expired code."""
    phone = "+1777888999"
    client.post("/auth/send-otp", json={"phone_number": phone})

    # Set expiry into the past
    otp_record = db_session.query(OTPCode).filter(OTPCode.identifier == phone).first()
    otp_record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    db_session.commit()

    verify_resp = client.post("/auth/verify-otp", json={
        "phone_number": phone,
        "otp_code": otp_record.otp_code,
    })
    assert verify_resp.status_code == 400
    assert "expired" in verify_resp.json()["detail"]


def test_get_me_success(client: TestClient, db_session: Session):
    """Test GET /auth/me with valid Bearer JWT access token."""
    phone = "+1122334455"
    client.post("/auth/send-otp", json={"phone_number": phone})
    otp_record = db_session.query(OTPCode).filter(OTPCode.identifier == phone).first()

    verify_resp = client.post("/auth/verify-otp", json={
        "phone_number": phone,
        "otp_code": otp_record.otp_code,
    })
    access_token = verify_resp.json()["access_token"]

    # Request /auth/me
    headers = {"Authorization": f"Bearer {access_token}"}
    me_resp = client.get("/auth/me", headers=headers)
    assert me_resp.status_code == 200
    user_data = me_resp.json()
    assert user_data["phone_number"] == phone
    assert user_data["is_verified"] is True
    assert user_data["profile"] is not None


def test_get_me_unauthorized(client: TestClient):
    """Test GET /auth/me without token and with invalid token."""
    # Without token
    no_auth_resp = client.get("/auth/me")
    assert no_auth_resp.status_code == 401

    # With invalid token
    bad_auth_resp = client.get("/auth/me", headers={"Authorization": "Bearer invalid_token_xyz"})
    assert bad_auth_resp.status_code == 401


def test_get_me_with_refresh_token_fails(client: TestClient, db_session: Session):
    """Test GET /auth/me rejects refresh tokens."""
    phone = "+1999111222"
    client.post("/auth/send-otp", json={"phone_number": phone})
    otp_record = db_session.query(OTPCode).filter(OTPCode.identifier == phone).first()

    verify_resp = client.post("/auth/verify-otp", json={
        "phone_number": phone,
        "otp_code": otp_record.otp_code,
    })
    refresh_token = verify_resp.json()["refresh_token"]

    headers = {"Authorization": f"Bearer {refresh_token}"}
    me_resp = client.get("/auth/me", headers=headers)
    assert me_resp.status_code == 401
    assert "Access token required" in me_resp.json()["detail"]


def test_refresh_token_success(client: TestClient, db_session: Session):
    """Test POST /auth/refresh-token rotates tokens and validates new access token."""
    phone = "+1333222111"
    client.post("/auth/send-otp", json={"phone_number": phone})
    otp_record = db_session.query(OTPCode).filter(OTPCode.identifier == phone).first()

    verify_resp = client.post("/auth/verify-otp", json={
        "phone_number": phone,
        "otp_code": otp_record.otp_code,
    })
    initial_refresh = verify_resp.json()["refresh_token"]

    # Refresh token
    refresh_resp = client.post("/auth/refresh-token", json={"refresh_token": initial_refresh})
    assert refresh_resp.status_code == 200
    refresh_data = refresh_resp.json()
    new_access = refresh_data["access_token"]
    new_refresh = refresh_data["refresh_token"]
    assert new_access is not None
    assert new_refresh is not None
    assert new_refresh != initial_refresh

    # Test new access token against /auth/me
    headers = {"Authorization": f"Bearer {new_access}"}
    me_resp = client.get("/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["phone_number"] == phone

    # Old refresh token should now be revoked
    old_refresh_resp = client.post("/auth/refresh-token", json={"refresh_token": initial_refresh})
    assert old_refresh_resp.status_code == 401


def test_refresh_token_invalid(client: TestClient):
    """Test POST /auth/refresh-token with garbage token."""
    resp = client.post("/auth/refresh-token", json={"refresh_token": "random_junk_token"})
    assert resp.status_code == 401


def test_logout_success(client: TestClient, db_session: Session):
    """Test POST /auth/logout revokes session so refresh token is no longer usable."""
    phone = "+1444555666"
    client.post("/auth/send-otp", json={"phone_number": phone})
    otp_record = db_session.query(OTPCode).filter(OTPCode.identifier == phone).first()

    verify_resp = client.post("/auth/verify-otp", json={
        "phone_number": phone,
        "otp_code": otp_record.otp_code,
    })
    access_token = verify_resp.json()["access_token"]
    refresh_token = verify_resp.json()["refresh_token"]

    # Logout
    logout_resp = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"refresh_token": refresh_token},
    )
    assert logout_resp.status_code == 200
    assert logout_resp.json()["message"] == "Logged out successfully."

    # Verify refresh token is revoked
    refresh_resp = client.post("/auth/refresh-token", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 401


def test_verify_otp_max_attempts_exceeded(client: TestClient, db_session: Session):
    """Test OTP invalidation when maximum attempts limit is exceeded."""
    phone = "+1888999000"
    client.post("/auth/send-otp", json={"phone_number": phone})
    otp_record = db_session.query(OTPCode).filter(OTPCode.identifier == phone).first()
    real_code = otp_record.otp_code

    # Fail 5 times
    for _ in range(5):
        resp = client.post("/auth/verify-otp", json={
            "phone_number": phone,
            "otp_code": "000000",
        })
        assert resp.status_code == 400

    # 6th attempt with real code must fail because max attempts exceeded
    exceeded_resp = client.post("/auth/verify-otp", json={
        "phone_number": phone,
        "otp_code": real_code,
    })
    assert exceeded_resp.status_code == 400
    assert "exceeded" in exceeded_resp.json()["detail"].lower() or "active" in exceeded_resp.json()["detail"].lower()


def test_logout_all_sessions_without_body(client: TestClient, db_session: Session):
    """Test POST /auth/logout without body revokes all sessions for user."""
    phone = "+1999888777"
    client.post("/auth/send-otp", json={"phone_number": phone})
    otp_record = db_session.query(OTPCode).filter(OTPCode.identifier == phone).first()

    verify_resp = client.post("/auth/verify-otp", json={
        "phone_number": phone,
        "otp_code": otp_record.otp_code,
    })
    access_token = verify_resp.json()["access_token"]
    refresh_token = verify_resp.json()["refresh_token"]

    # Logout without body
    logout_resp = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert logout_resp.status_code == 200
    assert logout_resp.json()["message"] == "Logged out successfully."

    # Refresh token should now be revoked
    refresh_resp = client.post("/auth/refresh-token", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 401


def test_health_check(client: TestClient):
    """Test GET /health returns 200 OK status."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_verify_otp_existing_user_login(client: TestClient, db_session: Session):
    """Test that an existing user can log in with a new OTP without duplication."""
    phone = "+12025550199"
    # First login (registration)
    client.post("/auth/send-otp", json={"phone_number": phone})
    otp1 = db_session.query(OTPCode).filter(OTPCode.identifier == phone).first().otp_code
    resp1 = client.post("/auth/verify-otp", json={"phone_number": phone, "otp_code": otp1})
    assert resp1.status_code == 200
    user_id_1 = resp1.json()["user"]["id"]

    # Second login
    client.post("/auth/send-otp", json={"phone_number": phone})
    otp2 = db_session.query(OTPCode).filter(OTPCode.identifier == phone, OTPCode.is_used == False).first().otp_code
    resp2 = client.post("/auth/verify-otp", json={"phone_number": phone, "otp_code": otp2})
    assert resp2.status_code == 200
    user_id_2 = resp2.json()["user"]["id"]
    assert user_id_1 == user_id_2

    # Total users in DB should still be 1
    assert db_session.query(User).count() == 1


def test_send_otp_invalidates_previous_otp(client: TestClient, db_session: Session):
    """Test that requesting a second OTP invalidates the first OTP."""
    phone = "+1555000111"
    # First OTP
    client.post("/auth/send-otp", json={"phone_number": phone})
    otp1 = db_session.query(OTPCode).filter(OTPCode.identifier == phone).order_by(OTPCode.created_at.desc()).first().otp_code

    # Second OTP
    client.post("/auth/send-otp", json={"phone_number": phone})
    db_session.expire_all()
    otp2 = db_session.query(OTPCode).filter(OTPCode.identifier == phone, OTPCode.is_used == False).order_by(OTPCode.created_at.desc()).first().otp_code
    assert otp1 != otp2

    # Attempting to use the old OTP1 must fail
    resp_old = client.post("/auth/verify-otp", json={"phone_number": phone, "otp_code": otp1})
    assert resp_old.status_code == 400

    # Using the new OTP2 must succeed
    resp_new = client.post("/auth/verify-otp", json={"phone_number": phone, "otp_code": otp2})
    assert resp_new.status_code == 200


def test_refresh_token_with_access_token_fails(client: TestClient, db_session: Session):
    """Test that passing an access token to /auth/refresh-token is rejected."""
    phone = "+1555000222"
    client.post("/auth/send-otp", json={"phone_number": phone})
    otp = db_session.query(OTPCode).filter(OTPCode.identifier == phone).first().otp_code
    auth_resp = client.post("/auth/verify-otp", json={"phone_number": phone, "otp_code": otp})
    access_token = auth_resp.json()["access_token"]

    # Try to use access token as refresh token
    refresh_resp = client.post("/auth/refresh-token", json={"refresh_token": access_token})
    assert refresh_resp.status_code == 401


def test_refresh_token_inactive_user_fails(client: TestClient, db_session: Session):
    """Test that an inactive user cannot refresh tokens."""
    phone = "+1555000333"
    client.post("/auth/send-otp", json={"phone_number": phone})
    otp = db_session.query(OTPCode).filter(OTPCode.identifier == phone).first().otp_code
    auth_resp = client.post("/auth/verify-otp", json={"phone_number": phone, "otp_code": otp})
    refresh_token = auth_resp.json()["refresh_token"]
    user_id = auth_resp.json()["user"]["id"]

    # Deactivate user
    user = db_session.query(User).filter(User.id == user_id).first()
    user.is_active = False
    db_session.commit()

    # Attempt refresh
    refresh_resp = client.post("/auth/refresh-token", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 401
    assert "inactive" in refresh_resp.json()["detail"].lower()


def test_logout_cross_user_isolation(client: TestClient, db_session: Session):
    """Test that User A cannot revoke User B's session."""
    phone_a = "+1555000444"
    phone_b = "+1555000555"

    # User A login
    client.post("/auth/send-otp", json={"phone_number": phone_a})
    otp_a = db_session.query(OTPCode).filter(OTPCode.identifier == phone_a).first().otp_code
    resp_a = client.post("/auth/verify-otp", json={"phone_number": phone_a, "otp_code": otp_a})
    token_a = resp_a.json()["access_token"]

    # User B login
    client.post("/auth/send-otp", json={"phone_number": phone_b})
    db_session.expire_all()
    otp_b = db_session.query(OTPCode).filter(OTPCode.identifier == phone_b).first().otp_code
    resp_b = client.post("/auth/verify-otp", json={"phone_number": phone_b, "otp_code": otp_b})
    token_b_refresh = resp_b.json()["refresh_token"]

    # User A attempts to revoke User B's refresh token
    logout_attempt = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"refresh_token": token_b_refresh},
    )
    assert logout_attempt.status_code == 200

    # User B's refresh token should STILL work because User A is not allowed to revoke it
    refresh_b_resp = client.post("/auth/refresh-token", json={"refresh_token": token_b_refresh})
    assert refresh_b_resp.status_code == 200


def test_get_me_inactive_user_fails(client: TestClient, db_session: Session):
    """Test that an inactive user is rejected from GET /auth/me."""
    phone = "+1555000666"
    client.post("/auth/send-otp", json={"phone_number": phone})
    otp = db_session.query(OTPCode).filter(OTPCode.identifier == phone).first().otp_code
    auth_resp = client.post("/auth/verify-otp", json={"phone_number": phone, "otp_code": otp})
    access_token = auth_resp.json()["access_token"]
    user_id = auth_resp.json()["user"]["id"]

    # Deactivate user
    user = db_session.query(User).filter(User.id == user_id).first()
    user.is_active = False
    db_session.commit()

    me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me_resp.status_code == 401
    assert "inactive" in me_resp.json()["detail"].lower()


def test_verify_otp_invalid_empty_fields(client: TestClient):
    """Test that whitespace-only identifiers or missing fields return 422."""
    resp_send = client.post("/auth/send-otp", json={"phone_number": "   "})
    assert resp_send.status_code == 422

    resp_verify = client.post("/auth/verify-otp", json={"phone_number": "   ", "otp_code": "123456"})
    assert resp_verify.status_code == 422


def test_send_and_verify_otp_email_case_insensitivity(client: TestClient, db_session: Session):
    """Test that uppercase email in send-otp works seamlessly with lowercase email in verify-otp."""
    upper_email = "Shopper.VIP@Spreego.COM"
    lower_email = "shopper.vip@spreego.com"

    send_resp = client.post("/auth/send-otp", json={"email": upper_email})
    assert send_resp.status_code == 200
    assert send_resp.json()["identifier"] == lower_email

    otp_record = db_session.query(OTPCode).filter(OTPCode.identifier == lower_email).first()
    assert otp_record is not None

    verify_resp = client.post("/auth/verify-otp", json={
        "email": lower_email,
        "otp_code": otp_record.otp_code,
    })
    assert verify_resp.status_code == 200
    user_data = verify_resp.json()["user"]
    assert user_data["email"] == lower_email


def test_whitespace_field_shadowing_valid_identifier(client: TestClient, db_session: Session):
    """Test that whitespace in unused fields does not mask or shadow a valid identifier."""
    email = "valid_customer@spreego.com"
    send_resp = client.post("/auth/send-otp", json={"phone_number": "   ", "email": email})
    assert send_resp.status_code == 200
    assert send_resp.json()["identifier"] == email

    otp = db_session.query(OTPCode).filter(OTPCode.identifier == email).first().otp_code

    verify_resp = client.post("/auth/verify-otp", json={
        "phone_number": "   ",
        "email": email,
        "otp_code": otp,
    })
    assert verify_resp.status_code == 200
    assert verify_resp.json()["user"]["email"] == email


def test_logout_unauthorized(client: TestClient):
    """Test that POST /auth/logout rejects missing or whitespace credentials with 401."""
    # No auth header
    resp_no_auth = client.post("/auth/logout")
    assert resp_no_auth.status_code == 401

    # Whitespace token
    resp_whitespace = client.post("/auth/logout", headers={"Authorization": "Bearer   "})
    assert resp_whitespace.status_code == 401


def test_refresh_token_expired_db_session(client: TestClient, db_session: Session):
    """Test that a refresh token whose database session expired is rejected with 401."""
    phone = "+1555123999"
    client.post("/auth/send-otp", json={"phone_number": phone})
    otp = db_session.query(OTPCode).filter(OTPCode.identifier == phone).first().otp_code
    auth_resp = client.post("/auth/verify-otp", json={"phone_number": phone, "otp_code": otp})
    refresh_token = auth_resp.json()["refresh_token"]

    # Manually expire session in DB
    session = db_session.query(UserSession).filter(UserSession.refresh_token == refresh_token).first()
    assert session is not None
    session.expires_at = datetime.now(timezone.utc) - timedelta(days=2)
    db_session.commit()

    # Attempt to refresh
    refresh_resp = client.post("/auth/refresh-token", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 401
    assert "expired" in refresh_resp.json()["detail"].lower()


def test_profile_username_sanitization(client: TestClient, db_session: Session):
    """Test that generated username from special character email is sanitized to alphanumeric and underscores."""
    email = "deal-hunter+vip!2026@spreego.com"
    client.post("/auth/send-otp", json={"email": email})
    otp = db_session.query(OTPCode).filter(OTPCode.identifier == email).first().otp_code
    auth_resp = client.post("/auth/verify-otp", json={"email": email, "otp_code": otp})
    assert auth_resp.status_code == 200

    username = auth_resp.json()["user"]["profile"]["username"]
    assert username is not None
    # Must only contain letters, digits, and underscores
    assert re.match(r"^[a-zA-Z0-9_]+$", username) is not None
    assert "+" not in username
    assert "!" not in username
    assert "-" not in username


def test_self_healing_missing_profile(client: TestClient, db_session: Session):
    """Test that a user lacking a profile is automatically self-healed on GET /auth/me."""
    user = User(
        phone_number="+1999777555",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Ensure profile is missing
    assert user.profile is None

    token = create_access_token(user_id=user.id)
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["profile"] is not None
    assert data["profile"]["username"] is not None


def test_otp_immediate_invalidation_on_fifth_failed_attempt(client: TestClient, db_session: Session):
    """Test that the 5th failed OTP attempt immediately marks the OTP code as used."""
    phone = "+1555666777"
    client.post("/auth/send-otp", json={"phone_number": phone})
    otp_record = db_session.query(OTPCode).filter(OTPCode.identifier == phone).first()
    assert otp_record.is_used is False

    for attempt in range(5):
        resp = client.post("/auth/verify-otp", json={"phone_number": phone, "otp_code": "000000"})
        assert resp.status_code == 400

    # Verify directly from DB that is_used became True immediately
    db_session.expire_all()
    otp_record = db_session.query(OTPCode).filter(OTPCode.identifier == phone).first()
    assert otp_record.attempts == 5
    assert otp_record.is_used is True


def test_concurrent_otp_race_condition_protection(client: TestClient, db_session: Session):
    """Test that concurrent overlapping active OTPs are safely swept and older active OTP cannot be replayed."""
    phone = "+1555987654"
    # Seed an older unverified OTP record
    older_otp = OTPCode(
        identifier=phone,
        otp_code="111111",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        is_used=False,
        attempts=0,
        created_at=datetime.now(timezone.utc) - timedelta(seconds=10),
    )
    db_session.add(older_otp)
    db_session.commit()

    # User issues send-otp creating a newer OTP record
    send_resp = client.post("/auth/send-otp", json={"phone_number": phone})
    assert send_resp.status_code == 200

    db_session.expire_all()
    newer_otp = (
        db_session.query(OTPCode)
        .filter(OTPCode.identifier == phone, OTPCode.is_used == False)
        .order_by(OTPCode.created_at.desc())
        .first()
    )
    assert newer_otp.otp_code != "111111"

    # Verifying with the newer OTP must succeed
    verify_resp = client.post("/auth/verify-otp", json={
        "phone_number": phone,
        "otp_code": newer_otp.otp_code,
    })
    assert verify_resp.status_code == 200

    # Attempting to use the older OTP must fail because it was purged
    older_resp = client.post("/auth/verify-otp", json={
        "phone_number": phone,
        "otp_code": "111111",
    })
    assert older_resp.status_code == 400


def test_logout_whitespace_token_does_not_revoke_other_sessions(client: TestClient, db_session: Session):
    """Test that passing a whitespace refresh_token to logout does not collateral-revoke active user sessions."""
    phone = "+1555999888"
    client.post("/auth/send-otp", json={"phone_number": phone})
    otp = db_session.query(OTPCode).filter(OTPCode.identifier == phone).first().otp_code
    auth_resp = client.post("/auth/verify-otp", json={"phone_number": phone, "otp_code": otp})
    access_token = auth_resp.json()["access_token"]
    refresh_1 = auth_resp.json()["refresh_token"]

    # Rotate to create a second active session
    rot_resp = client.post("/auth/refresh-token", json={"refresh_token": refresh_1})
    assert rot_resp.status_code == 200
    access_2 = rot_resp.json()["access_token"]
    refresh_2 = rot_resp.json()["refresh_token"]

    # Logout with whitespace token in body
    logout_resp = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {access_2}"},
        json={"refresh_token": "   "},
    )
    assert logout_resp.status_code == 200

    # The active session refresh_2 must NOT be revoked
    check_resp = client.post("/auth/refresh-token", json={"refresh_token": refresh_2})
    assert check_resp.status_code == 200


def test_profile_username_fallback_for_symbol_only_email(client: TestClient, db_session: Session):
    """Test that email prefix containing only special symbols cleanly falls back to 'user_<suffix>'."""
    email = "...@spreego.com"
    client.post("/auth/send-otp", json={"email": email})
    otp = db_session.query(OTPCode).filter(OTPCode.identifier == email).first().otp_code
    verify_resp = client.post("/auth/verify-otp", json={"email": email, "otp_code": otp})
    assert verify_resp.status_code == 200

    username = verify_resp.json()["user"]["profile"]["username"]
    assert username is not None
    assert username.startswith("user_")
    assert re.match(r"^user_[a-zA-Z0-9_]+$", username) is not None


def test_get_me_unsupported_auth_scheme(client: TestClient):
    """Test GET /auth/me with unsupported auth scheme (e.g. Basic) returns 401."""
    resp = client.get("/auth/me", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert resp.status_code == 401
    assert "Bearer" in resp.headers.get("WWW-Authenticate", "")


def test_decode_token_empty_and_invalid():
    """Test that decode_token raises TokenInvalidError on empty or corrupted strings."""
    with pytest.raises(TokenInvalidError):
        decode_token("")

    with pytest.raises(TokenInvalidError):
        decode_token("   ")

    with pytest.raises(TokenInvalidError):
        decode_token("completely.invalid.token")


