import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.config.security import create_access_token
from src.models.notification import Notification, NotificationType
from src.models.profile import Profile
from src.models.user import User
from src.services.notification_service import NotificationService


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
# Notification Service & Creation Tests
# ============================================================================

def test_notification_service_create_and_dispatch(db_session: Session):
    """Test NotificationService dispatch and create_notification helper."""
    user = create_test_user(db_session, username="notif_user_1")
    actor = create_test_user(db_session, username="notif_actor_1")

    # Instance method
    service = NotificationService(db_session)
    n1 = service.create_notification(
        recipient_id=user.id,
        type=NotificationType.CLAP,
        title="New Clap",
        message="Someone clapped your spree!",
        actor_id=actor.id,
        entity_id="spree-123",
        entity_type="spree",
    )
    assert n1.id is not None
    assert n1.recipient_id == user.id
    assert n1.actor_id == actor.id
    assert n1.type == NotificationType.CLAP
    assert n1.is_read is False

    # Classmethod dispatch helper
    n2 = NotificationService.dispatch(
        db=db_session,
        recipient_id=user.id,
        type=NotificationType.ORDER_PLACED,
        title="Order Placed",
        message="Your order #100 has been placed.",
        entity_id="order-100",
        entity_type="order",
    )
    assert n2.id is not None
    assert n2.type == NotificationType.ORDER_PLACED
    assert n2.actor_id is None


def test_notification_service_validation_errors(db_session: Session):
    """Test validation errors on missing required fields in NotificationService."""
    service = NotificationService(db_session)
    with pytest.raises(ValueError, match="recipient_id is required"):
        service.create_notification(recipient_id="", type="SYSTEM", title="T", message="M")

    with pytest.raises(ValueError, match="title is required"):
        service.create_notification(recipient_id="uid", type="SYSTEM", title="", message="M")

    with pytest.raises(ValueError, match="message is required"):
        service.create_notification(recipient_id="uid", type="SYSTEM", title="T", message="")


# ============================================================================
# API Endpoints: Listing, Filtering & Pagination
# ============================================================================

def test_get_notifications_empty(client: TestClient, db_session: Session):
    """Test fetching notifications when user has none."""
    user = create_test_user(db_session, username="empty_notif_user")
    response = client.get("/api/v1/notifications", headers=auth_headers(user.id))
    assert response.status_code == 200
    assert response.json() == []


def test_get_notifications_paginated_and_sorted(client: TestClient, db_session: Session):
    """Test pagination and ordering of notifications (descending by created_at)."""
    user = create_test_user(db_session, username="paging_user")
    service = NotificationService(db_session)

    created_ids = []
    for i in range(5):
        notif = service.create_notification(
            recipient_id=user.id,
            type=NotificationType.SYSTEM,
            title=f"Notification {i}",
            message=f"Message {i}",
        )
        created_ids.append(notif.id)

    # Fetch page 1 with limit 2
    res_p1 = client.get("/api/v1/notifications?limit=2&skip=0", headers=auth_headers(user.id))
    assert res_p1.status_code == 200
    data_p1 = res_p1.json()
    assert len(data_p1) == 2
    # Newest first
    assert data_p1[0]["id"] == created_ids[4]
    assert data_p1[1]["id"] == created_ids[3]

    # Fetch page 2 using page query param
    res_p2 = client.get("/api/v1/notifications?page=2&limit=2", headers=auth_headers(user.id))
    assert res_p2.status_code == 200
    data_p2 = res_p2.json()
    assert len(data_p2) == 2
    assert data_p2[0]["id"] == created_ids[2]
    assert data_p2[1]["id"] == created_ids[1]


def test_get_notifications_filtering(client: TestClient, db_session: Session):
    """Test filtering notifications by unread_only and type."""
    user = create_test_user(db_session, username="filter_user")
    service = NotificationService(db_session)

    n1 = service.create_notification(
        recipient_id=user.id,
        type=NotificationType.CLAP,
        title="Clap 1",
        message="M1",
    )
    n2 = service.create_notification(
        recipient_id=user.id,
        type=NotificationType.COMMENT,
        title="Comment 1",
        message="M2",
    )
    # Mark n1 as read
    service.mark_as_read(n1.id, user)

    # Filter unread only
    res_unread = client.get("/api/v1/notifications?unread_only=true", headers=auth_headers(user.id))
    assert res_unread.status_code == 200
    unread_data = res_unread.json()
    assert len(unread_data) == 1
    assert unread_data[0]["id"] == n2.id

    # Filter read only
    res_read = client.get("/api/v1/notifications?unread_only=false", headers=auth_headers(user.id))
    assert res_read.status_code == 200
    read_data = res_read.json()
    assert len(read_data) == 1
    assert read_data[0]["id"] == n1.id

    # Filter by type
    res_type = client.get("/api/v1/notifications?type=COMMENT", headers=auth_headers(user.id))
    assert res_type.status_code == 200
    type_data = res_type.json()
    assert len(type_data) == 1
    assert type_data[0]["type"] == "COMMENT"


# ============================================================================
# API Endpoints: Unread Counter
# ============================================================================

def test_unread_count_badge(client: TestClient, db_session: Session):
    """Test unread badge counter reflects real count accurately."""
    user = create_test_user(db_session, username="badge_user")
    service = NotificationService(db_session)

    # Initial count = 0
    res0 = client.get("/api/v1/notifications/unread-count", headers=auth_headers(user.id))
    assert res0.status_code == 200
    assert res0.json() == {"unread_count": 0}

    # Add 3 notifications
    n1 = service.create_notification(recipient_id=user.id, type=NotificationType.SYSTEM, title="T1", message="M1")
    n2 = service.create_notification(recipient_id=user.id, type=NotificationType.SYSTEM, title="T2", message="M2")
    n3 = service.create_notification(recipient_id=user.id, type=NotificationType.SYSTEM, title="T3", message="M3")

    res3 = client.get("/api/v1/notifications/unread-count", headers=auth_headers(user.id))
    assert res3.status_code == 200
    assert res3.json() == {"unread_count": 3}

    # Mark 1 as read
    client.patch(f"/api/v1/notifications/{n1.id}/read", headers=auth_headers(user.id))
    res2 = client.get("/api/v1/notifications/unread-count", headers=auth_headers(user.id))
    assert res2.status_code == 200
    assert res2.json() == {"unread_count": 2}


# ============================================================================
# API Endpoints: Mark Single and All as Read
# ============================================================================

def test_mark_single_notification_as_read(client: TestClient, db_session: Session):
    """Test marking a single notification as read."""
    user = create_test_user(db_session, username="mark_single_user")
    service = NotificationService(db_session)

    notif = service.create_notification(recipient_id=user.id, type=NotificationType.PAYOUT, title="Payout", message="Processed")
    assert notif.is_read is False

    response = client.patch(f"/api/v1/notifications/{notif.id}/read", headers=auth_headers(user.id))
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == notif.id
    assert data["is_read"] is True

    # Calling read again is idempotent
    response_again = client.patch(f"/api/v1/notifications/{notif.id}/read", headers=auth_headers(user.id))
    assert response_again.status_code == 200
    assert response_again.json()["is_read"] is True


def test_mark_all_notifications_as_read(client: TestClient, db_session: Session):
    """Test marking all notifications as read for current user with isolation."""
    user_a = create_test_user(db_session, username="read_all_a")
    user_b = create_test_user(db_session, username="read_all_b")
    service = NotificationService(db_session)

    # User A gets 3 notifications
    for i in range(3):
        service.create_notification(recipient_id=user_a.id, type=NotificationType.SYSTEM, title=f"A{i}", message=f"M{i}")

    # User B gets 2 notifications
    for i in range(2):
        service.create_notification(recipient_id=user_b.id, type=NotificationType.SYSTEM, title=f"B{i}", message=f"M{i}")

    # User A calls read-all
    res_a = client.post("/api/v1/notifications/read-all", headers=auth_headers(user_a.id))
    assert res_a.status_code == 200
    assert res_a.json()["updated_count"] == 3

    # Check User A unread count is 0
    count_a = client.get("/api/v1/notifications/unread-count", headers=auth_headers(user_a.id)).json()["unread_count"]
    assert count_a == 0

    # User B notifications MUST remain untouched (count = 2)
    count_b = client.get("/api/v1/notifications/unread-count", headers=auth_headers(user_b.id)).json()["unread_count"]
    assert count_b == 2


# ============================================================================
# Security Isolation & Authorization Tests
# ============================================================================

def test_notification_security_isolation_cross_user_forbidden(client: TestClient, db_session: Session):
    """Test that User B cannot mark or manipulate User A's notification (HTTP 403)."""
    user_a = create_test_user(db_session, username="owner_a")
    user_b = create_test_user(db_session, username="attacker_b")
    service = NotificationService(db_session)

    notif_a = service.create_notification(recipient_id=user_a.id, type=NotificationType.FOLLOW, title="Follow", message="New follower")

    # Attacker attempts to mark owner's notification as read
    response = client.patch(f"/api/v1/notifications/{notif_a.id}/read", headers=auth_headers(user_b.id))
    assert response.status_code == 403
    assert "access" in response.json()["detail"].lower()

    # User A notification is still unread
    count_a = client.get("/api/v1/notifications/unread-count", headers=auth_headers(user_a.id)).json()["unread_count"]
    assert count_a == 1


def test_notification_listing_isolation(client: TestClient, db_session: Session):
    """Test that User B's notification list does not include User A's notifications."""
    user_a = create_test_user(db_session, username="list_owner_a")
    user_b = create_test_user(db_session, username="list_viewer_b")
    service = NotificationService(db_session)

    service.create_notification(recipient_id=user_a.id, type=NotificationType.CLAP, title="Secret A", message="Private")

    # User B list must be empty
    response_b = client.get("/api/v1/notifications", headers=auth_headers(user_b.id))
    assert response_b.status_code == 200
    assert response_b.json() == []


def test_mark_nonexistent_notification_returns_404(client: TestClient, db_session: Session):
    """Test that marking a nonexistent notification returns 404."""
    user = create_test_user(db_session, username="notif_404_user")
    response = client.patch("/api/v1/notifications/non-existent-id/read", headers=auth_headers(user.id))
    assert response.status_code == 404


def test_unauthenticated_requests_rejected(client: TestClient):
    """Test that all notification endpoints require authentication (401)."""
    assert client.get("/api/v1/notifications").status_code == 401
    assert client.get("/api/v1/notifications/unread-count").status_code == 401
    assert client.patch("/api/v1/notifications/123/read").status_code == 401
    assert client.post("/api/v1/notifications/read-all").status_code == 401


# ============================================================================
# Enum Coverage Tests
# ============================================================================

def test_all_notification_types(db_session: Session):
    """Verify that all 8 NotificationType enums can be created and stored properly."""
    user = create_test_user(db_session, username="enum_user")
    service = NotificationService(db_session)

    for ntype in NotificationType:
        notif = service.create_notification(
            recipient_id=user.id,
            type=ntype,
            title=f"Test {ntype.value}",
            message=f"Message for {ntype.value}",
        )
        assert notif.type == ntype


# ============================================================================
# Additional Edge Case Tests
# ============================================================================

def test_read_all_when_no_notifications(client: TestClient, db_session: Session):
    """Test read-all when user has 0 notifications returns updated_count = 0."""
    user = create_test_user(db_session, username="zero_notifs_user")
    res = client.post("/api/v1/notifications/read-all", headers=auth_headers(user.id))
    assert res.status_code == 200
    assert res.json()["updated_count"] == 0


def test_read_all_when_already_all_read(client: TestClient, db_session: Session):
    """Test read-all when all notifications are already read returns updated_count = 0."""
    user = create_test_user(db_session, username="already_read_user")
    service = NotificationService(db_session)
    n = service.create_notification(recipient_id=user.id, type=NotificationType.SYSTEM, title="T", message="M")
    service.mark_as_read(n.id, user)

    res = client.post("/api/v1/notifications/read-all", headers=auth_headers(user.id))
    assert res.status_code == 200
    assert res.json()["updated_count"] == 0


def test_notification_pagination_boundaries(client: TestClient, db_session: Session):
    """Test query parameter validation on limit and page."""
    user = create_test_user(db_session, username="boundary_user")
    # page < 1
    assert client.get("/api/v1/notifications?page=0", headers=auth_headers(user.id)).status_code == 422
    # limit > 100
    assert client.get("/api/v1/notifications?limit=101", headers=auth_headers(user.id)).status_code == 422
    # limit < 1
    assert client.get("/api/v1/notifications?limit=0", headers=auth_headers(user.id)).status_code == 422


def test_notification_with_entity_and_actor(client: TestClient, db_session: Session):
    """Test retrieving notification with full entity and actor details."""
    user = create_test_user(db_session, username="full_notif_user")
    actor = create_test_user(db_session, username="full_notif_actor")
    service = NotificationService(db_session)

    n = service.create_notification(
        recipient_id=user.id,
        actor_id=actor.id,
        type=NotificationType.COMMENT,
        title="New comment",
        message="Someone commented on your spree",
        entity_id="spree-xyz",
        entity_type="spree",
    )

    res = client.get("/api/v1/notifications", headers=auth_headers(user.id))
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert items[0]["id"] == n.id
    assert items[0]["actor_id"] == actor.id
    assert items[0]["entity_id"] == "spree-xyz"
    assert items[0]["entity_type"] == "spree"


def test_create_notification_whitespace_rejected(db_session: Session):
    """Test that whitespace-only strings for required fields raise ValueError."""
    user = create_test_user(db_session, username="ws_notif_user")
    service = NotificationService(db_session)

    with pytest.raises(ValueError, match="recipient_id is required"):
        service.create_notification(recipient_id="   ", type="SYSTEM", title="T", message="M")

    with pytest.raises(ValueError, match="title is required"):
        service.create_notification(recipient_id=user.id, type="SYSTEM", title="   ", message="M")

    with pytest.raises(ValueError, match="message is required"):
        service.create_notification(recipient_id=user.id, type="SYSTEM", title="T", message="   ")


def test_create_notification_case_insensitive_type(db_session: Session):
    """Test that lowercase string type like 'clap' is automatically normalized to NotificationType.CLAP."""
    user = create_test_user(db_session, username="case_user")
    service = NotificationService(db_session)
    n = service.create_notification(recipient_id=user.id, type="clap", title="T", message="M")
    assert n.type == NotificationType.CLAP


def test_notification_class_call_variants(db_session: Session):
    """Test calling NotificationService.create_notification directly on the class with positional db and kwarg db."""
    user = create_test_user(db_session, username="class_call_user")

    # Positional db
    n1 = NotificationService.create_notification(
        db_session,
        recipient_id=user.id,
        type=NotificationType.SYSTEM,
        title="Positional DB",
        message="Message 1",
    )
    assert n1.id is not None
    assert n1.title == "Positional DB"

    # Kwarg db
    n2 = NotificationService.create_notification(
        db=db_session,
        recipient_id=user.id,
        type=NotificationType.SYSTEM,
        title="Kwarg DB",
        message="Message 2",
    )
    assert n2.id is not None
    assert n2.title == "Kwarg DB"


def test_notifications_deterministic_sort_order(client: TestClient, db_session: Session):
    """Test deterministic ordering by created_at desc, id desc when created_at is identical."""
    user = create_test_user(db_session, username="sort_user")
    service = NotificationService(db_session)

    n1 = service.create_notification(recipient_id=user.id, type=NotificationType.SYSTEM, title="T1", message="M1")
    n2 = service.create_notification(recipient_id=user.id, type=NotificationType.SYSTEM, title="T2", message="M2")

    # Force identical timestamps
    same_time = n1.created_at
    n2.created_at = same_time
    db_session.commit()

    res = client.get("/api/v1/notifications", headers=auth_headers(user.id))
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 2
    # Secondary order by id desc
    expected_first = n1.id if n1.id > n2.id else n2.id
    assert items[0]["id"] == expected_first


def test_create_notification_whitespace_actor_and_entity_nullified(db_session: Session):
    """Test that empty or whitespace-only actor_id, entity_id, and entity_type are stored as None (NULL)."""
    user = create_test_user(db_session, username="null_fields_user")
    service = NotificationService(db_session)

    notif = service.create_notification(
        recipient_id=user.id,
        type=NotificationType.SYSTEM,
        title="Valid Title",
        message="Valid Message",
        actor_id="   ",
        entity_id="   ",
        entity_type="   ",
    )
    assert notif.actor_id is None
    assert notif.entity_id is None
    assert notif.entity_type is None


def test_create_notification_positional_with_db_kwarg(db_session: Session):
    """Test calling NotificationService.create_notification with positional parameters and db=db_session kwarg."""
    user = create_test_user(db_session, username="pos_db_user")
    notif = NotificationService.create_notification(
        user.id,
        NotificationType.COMMENT,
        "Positional Title",
        "Positional Message",
        db=db_session,
    )
    assert notif.id is not None
    assert notif.recipient_id == user.id
    assert notif.type == NotificationType.COMMENT
    assert notif.title == "Positional Title"
    assert notif.message == "Positional Message"


def test_notifications_case_insensitive_query_param(client: TestClient, db_session: Session):
    """Test that GET /api/v1/notifications accepts lowercase type query params (e.g. ?type=follow)."""
    user = create_test_user(db_session, username="query_case_user")
    service = NotificationService(db_session)
    n = service.create_notification(recipient_id=user.id, type=NotificationType.FOLLOW, title="Followed", message="New fan")

    res = client.get("/api/v1/notifications?type=follow", headers=auth_headers(user.id))
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert items[0]["id"] == n.id
    assert items[0]["type"] == "FOLLOW"

