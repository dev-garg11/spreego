from datetime import datetime, timedelta, timezone
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from src.config.database import Base
from src.config.security import create_access_token
from src.config.settings import settings
from src.models.membership import (
    MembershipPlan,
    MembershipTierType,
    Subscription,
    SubscriptionStatus,
)
from src.models.profile import Profile
from src.models.user import User
from src.services.membership_service import MembershipService
from src.validations.membership_schemas import (
    CreateMembershipPlanRequest,
    SubscribeMembershipRequest,
    UpdateMembershipPlanRequest,
)
from src.controllers.membership_controller import MembershipController


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
    phone = phone_number or f"+9199{uid[:6]}"
    mail = email or f"creator_{uid}@spreego.com"
    handle = username or f"creator_{uid}"

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
        full_name=f"Creator {handle}",
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
# 1. Database & Metadata Verification
# ============================================================================

def test_membership_models_registered_in_base_metadata():
    """Verify membership_plans and subscriptions tables are present in Base metadata."""
    assert "membership_plans" in Base.metadata.tables
    assert "subscriptions" in Base.metadata.tables

    plan_table = Base.metadata.tables["membership_plans"]
    assert "id" in plan_table.columns
    assert "creator_id" in plan_table.columns
    assert "name" in plan_table.columns
    assert "monthly_price" in plan_table.columns
    assert "currency" in plan_table.columns
    assert "tier_type" in plan_table.columns
    assert "benefits" in plan_table.columns
    assert "is_active" in plan_table.columns

    sub_table = Base.metadata.tables["subscriptions"]
    assert "id" in sub_table.columns
    assert "plan_id" in sub_table.columns
    assert "user_id" in sub_table.columns
    assert "status" in sub_table.columns
    assert "current_period_start" in sub_table.columns
    assert "current_period_end" in sub_table.columns


def test_membership_model_instantiation(db_session: Session):
    """Direct model instantiation in database."""
    creator = create_test_user(db_session, username="instantiate_creator")
    now = datetime.now(timezone.utc)
    plan = MembershipPlan(
        creator_id=creator.id,
        name="Instantiate Pass",
        description="Direct instantiation",
        monthly_price=0.0,
        currency="INR",
        tier_type=MembershipTierType.FREE,
        benefits=["Benefit A", "Benefit B"],
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)

    assert plan.id is not None
    assert plan.monthly_price == 0.0
    assert plan.is_free is True
    assert plan.subscribers_count == 0
    assert plan.benefits == ["Benefit A", "Benefit B"]
    assert "Instantiate Pass" in repr(plan)

    subscriber = create_test_user(db_session, username="instantiate_subscriber")
    sub = Subscription(
        plan_id=plan.id,
        user_id=subscriber.id,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
        created_at=now,
        updated_at=now,
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)

    assert sub.id is not None
    assert sub.status == SubscriptionStatus.ACTIVE
    assert "ACTIVE" in repr(sub)
    assert plan.subscribers_count == 1


# ============================================================================
# 2. Plan Creation (POST /api/v1/memberships/plans)
# ============================================================================

def test_create_free_membership_plan_success(client: TestClient, db_session: Session):
    """Creator successfully creates a ₹0 Free Community Pass."""
    creator = create_test_user(db_session, username="rajesh_creator")
    payload = {
        "name": "Community Pass",
        "description": "Exclusive access to community posts and chat",
        "monthly_price": 0.0,
        "currency": "INR",
        "tier_type": "FREE",
        "benefits": ["Community Discord Access", "Supporter Badge", "Early Video Access"],
    }
    response = client.post(
        "/api/v1/memberships/plans",
        json=payload,
        headers=auth_headers(creator.id),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["creator_id"] == creator.id
    assert data["name"] == "Community Pass"
    assert data["description"] == "Exclusive access to community posts and chat"
    assert data["monthly_price"] == 0.0
    assert data["currency"] == "INR"
    assert data["tier_type"] == "FREE"
    assert data["is_active"] is True
    assert len(data["benefits"]) == 3
    assert data["creator"]["username"] == "rajesh_creator"
    assert data["subscribers_count"] == 0


def test_create_plan_price_omitted_defaults_to_zero(client: TestClient, db_session: Session):
    """Omitting price forces/defaults to 0.0 and tier_type to FREE."""
    creator = create_test_user(db_session, username="default_price_creator")
    payload = {
        "name": "Supporter Tier",
        "description": "Basic supporter tier",
    }
    response = client.post(
        "/api/v1/memberships/plans",
        json=payload,
        headers=auth_headers(creator.id),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["monthly_price"] == 0.0
    assert data["tier_type"] == "FREE"
    assert data["currency"] == "INR"


def test_create_plan_unauthenticated(client: TestClient):
    """Unauthenticated creation request returns 401."""
    response = client.post(
        "/api/v1/memberships/plans",
        json={"name": "No Auth Plan"},
    )
    assert response.status_code == 401


def test_create_plan_empty_name_validation(client: TestClient, db_session: Session):
    """Empty or missing plan name fails validation with 422."""
    creator = create_test_user(db_session)
    response = client.post(
        "/api/v1/memberships/plans",
        json={"name": "   "},
        headers=auth_headers(creator.id),
    )
    assert response.status_code == 422


def test_create_plan_deactivated_account(client: TestClient, db_session: Session):
    """Deactivated creator account cannot create plans (blocked at authentication perimeter)."""
    creator = create_test_user(db_session, is_active=False)
    response = client.post(
        "/api/v1/memberships/plans",
        json={"name": "Inactive User Plan"},
        headers=auth_headers(creator.id),
    )
    assert response.status_code in (401, 403)


def test_create_plan_service_level_deactivated_account(db_session: Session):
    """Direct service call rejects deactivated creator with PermissionError."""
    creator = create_test_user(db_session, is_active=False)
    service = MembershipService(db_session)
    payload = CreateMembershipPlanRequest(name="Service Direct Plan")
    with pytest.raises(PermissionError):
        service.create_plan(creator_id=creator.id, payload=payload)


# ============================================================================
# 3. VIP Protection & Feature Flag (ENABLE_PAID_MEMBERSHIPS)
# ============================================================================

def test_create_vip_plan_rejected_when_paid_disabled(client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch):
    """Reject VIP creation and price > 0 when ENABLE_PAID_MEMBERSHIPS is False."""
    monkeypatch.setattr(settings, "ENABLE_PAID_MEMBERSHIPS", False)
    creator = create_test_user(db_session, username="vip_creator")

    # Attempting tier_type VIP
    response1 = client.post(
        "/api/v1/memberships/plans",
        json={
            "name": "VIP Pass",
            "tier_type": "VIP",
            "monthly_price": 0.0,
        },
        headers=auth_headers(creator.id),
    )
    assert response1.status_code == 400
    assert "Paid VIP memberships are currently disabled" in response1.json()["detail"]

    # Attempting price > 0
    response2 = client.post(
        "/api/v1/memberships/plans",
        json={
            "name": "Supporter 499",
            "tier_type": "FREE",
            "monthly_price": 499.0,
        },
        headers=auth_headers(creator.id),
    )
    assert response2.status_code == 400
    assert "Paid VIP memberships are currently disabled" in response2.json()["detail"]


def test_public_plans_filter_out_vip_tiers_when_paid_disabled(client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch):
    """Directly seeded VIP plan is hidden from GET /api/v1/memberships/plans when paid is disabled."""
    monkeypatch.setattr(settings, "ENABLE_PAID_MEMBERSHIPS", False)
    creator = create_test_user(db_session, username="dual_tier_creator")

    # Seed 1 Free plan and 1 VIP plan directly
    free_plan = MembershipPlan(
        creator_id=creator.id,
        name="Free Community",
        monthly_price=0.0,
        tier_type=MembershipTierType.FREE,
        is_active=True,
    )
    vip_plan = MembershipPlan(
        creator_id=creator.id,
        name="VIP Exclusive",
        monthly_price=499.0,
        tier_type=MembershipTierType.VIP,
        is_active=True,
    )
    db_session.add_all([free_plan, vip_plan])
    db_session.commit()

    response = client.get(f"/api/v1/memberships/plans?creator_id={creator.id}")
    assert response.status_code == 200
    plans = response.json()
    assert len(plans) == 1
    assert plans[0]["name"] == "Free Community"
    assert plans[0]["tier_type"] == "FREE"


def test_get_single_vip_plan_hidden_from_public(client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch):
    """Public user requesting single VIP plan gets 404 when paid mode is inactive."""
    monkeypatch.setattr(settings, "ENABLE_PAID_MEMBERSHIPS", False)
    creator = create_test_user(db_session, username="secret_vip_creator")
    viewer = create_test_user(db_session, username="viewer_user")

    vip_plan = MembershipPlan(
        creator_id=creator.id,
        name="Secret VIP",
        monthly_price=999.0,
        tier_type=MembershipTierType.VIP,
        is_active=True,
    )
    db_session.add(vip_plan)
    db_session.commit()

    # Anonymous viewer
    resp_anon = client.get(f"/api/v1/memberships/plans/{vip_plan.id}")
    assert resp_anon.status_code == 404

    # Other authenticated user
    resp_viewer = client.get(
        f"/api/v1/memberships/plans/{vip_plan.id}",
        headers=auth_headers(viewer.id),
    )
    assert resp_viewer.status_code == 404

    # The creator themselves can view it
    resp_creator = client.get(
        f"/api/v1/memberships/plans/{vip_plan.id}",
        headers=auth_headers(creator.id),
    )
    assert resp_creator.status_code == 200
    assert resp_creator.json()["name"] == "Secret VIP"


def test_subscribe_to_vip_rejected_when_paid_disabled(client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch):
    """Attempting to subscribe to a VIP plan when paid mode is disabled returns 400."""
    monkeypatch.setattr(settings, "ENABLE_PAID_MEMBERSHIPS", False)
    creator = create_test_user(db_session, username="paid_author")
    fan = create_test_user(db_session, username="eager_fan")

    vip_plan = MembershipPlan(
        creator_id=creator.id,
        name="Locked VIP",
        monthly_price=299.0,
        tier_type=MembershipTierType.VIP,
        is_active=True,
    )
    db_session.add(vip_plan)
    db_session.commit()

    response = client.post(
        "/api/v1/memberships/subscribe",
        json={"plan_id": vip_plan.id},
        headers=auth_headers(fan.id),
    )
    assert response.status_code == 400
    assert "Paid VIP memberships are currently disabled" in response.json()["detail"]


def test_vip_plan_allowed_when_paid_flag_enabled(client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch):
    """When ENABLE_PAID_MEMBERSHIPS is True, creator can create VIP tier and users can see and subscribe."""
    monkeypatch.setattr(settings, "ENABLE_PAID_MEMBERSHIPS", True)
    creator = create_test_user(db_session, username="vip_enabled_creator")
    subscriber = create_test_user(db_session, username="vip_enabled_sub")

    # Creator creates VIP plan
    res_create = client.post(
        "/api/v1/memberships/plans",
        json={
            "name": "Gold VIP Pass",
            "description": "All perks + private livestreams",
            "monthly_price": 299.0,
            "currency": "INR",
            "tier_type": "VIP",
            "benefits": ["Private Livestream", "VIP Discord Role"],
        },
        headers=auth_headers(creator.id),
    )
    assert res_create.status_code == 201
    plan_data = res_create.json()
    assert plan_data["tier_type"] == "VIP"
    assert plan_data["monthly_price"] == 299.0

    # Query plans - VIP is included!
    res_list = client.get(f"/api/v1/memberships/plans?creator_id={creator.id}")
    assert res_list.status_code == 200
    assert len(res_list.json()) == 1
    assert res_list.json()[0]["name"] == "Gold VIP Pass"

    # Subscribe to VIP plan
    res_sub = client.post(
        "/api/v1/memberships/subscribe",
        json={"plan_id": plan_data["id"]},
        headers=auth_headers(subscriber.id),
    )
    assert res_sub.status_code == 201
    assert res_sub.json()["status"] == "ACTIVE"


# ============================================================================
# 4. Listing Plans (GET /api/v1/memberships/plans)
# ============================================================================

def test_list_plans_by_creator(client: TestClient, db_session: Session):
    """Query available plans filtered by creator_id."""
    creator1 = create_test_user(db_session, username="creator_alpha")
    creator2 = create_test_user(db_session, username="creator_beta")

    p1 = MembershipPlan(creator_id=creator1.id, name="Alpha Tier 1", monthly_price=0.0, tier_type=MembershipTierType.FREE)
    p2 = MembershipPlan(creator_id=creator1.id, name="Alpha Tier 2", monthly_price=0.0, tier_type=MembershipTierType.FREE)
    p3 = MembershipPlan(creator_id=creator2.id, name="Beta Tier", monthly_price=0.0, tier_type=MembershipTierType.FREE)
    db_session.add_all([p1, p2, p3])
    db_session.commit()

    # Query creator1 plans
    resp1 = client.get(f"/api/v1/memberships/plans?creator_id={creator1.id}")
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert len(data1) == 2
    assert all(item["creator_id"] == creator1.id for item in data1)

    # Query creator2 plans
    resp2 = client.get(f"/api/v1/memberships/plans?creator_id={creator2.id}")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2) == 1
    assert data2[0]["name"] == "Beta Tier"


def test_list_plans_empty_for_creator_without_plans(client: TestClient, db_session: Session):
    """Creator with no plans returns an empty list."""
    creator = create_test_user(db_session, username="empty_plans_creator")
    response = client.get(f"/api/v1/memberships/plans?creator_id={creator.id}")
    assert response.status_code == 200
    assert response.json() == []


def test_list_plans_excludes_inactive_plans(client: TestClient, db_session: Session):
    """Deactivated plans are excluded from public listing."""
    creator = create_test_user(db_session, username="inactive_plan_creator")
    p_active = MembershipPlan(creator_id=creator.id, name="Active Plan", monthly_price=0.0, is_active=True)
    p_inactive = MembershipPlan(creator_id=creator.id, name="Deactivated Plan", monthly_price=0.0, is_active=False)
    db_session.add_all([p_active, p_inactive])
    db_session.commit()

    response = client.get(f"/api/v1/memberships/plans?creator_id={creator.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Active Plan"


# ============================================================================
# 5. Instant Seamless Subscription Flow (POST /api/v1/memberships/subscribe)
# ============================================================================

def test_instant_subscription_to_free_plan(client: TestClient, db_session: Session):
    """User instantly subscribes to ₹0 plan without payment friction, status ACTIVE."""
    creator = create_test_user(db_session, username="instant_creator")
    subscriber = create_test_user(db_session, username="instant_sub")

    plan = MembershipPlan(
        creator_id=creator.id,
        name="Free Pass",
        monthly_price=0.0,
        tier_type=MembershipTierType.FREE,
        is_active=True,
    )
    db_session.add(plan)
    db_session.commit()

    response = client.post(
        "/api/v1/memberships/subscribe",
        json={"plan_id": plan.id},
        headers=auth_headers(subscriber.id),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["plan_id"] == plan.id
    assert data["user_id"] == subscriber.id
    assert data["status"] == "ACTIVE"
    assert data["current_period_start"] is not None
    assert data["current_period_end"] is not None
    assert data["plan"]["name"] == "Free Pass"


def test_subscribe_unauthenticated(client: TestClient, db_session: Session):
    """Unauthenticated subscription request returns 401."""
    creator = create_test_user(db_session)
    plan = MembershipPlan(creator_id=creator.id, name="Free", monthly_price=0.0)
    db_session.add(plan)
    db_session.commit()

    response = client.post(
        "/api/v1/memberships/subscribe",
        json={"plan_id": plan.id},
    )
    assert response.status_code == 401


def test_subscribe_to_nonexistent_plan(client: TestClient, db_session: Session):
    """Subscribing to nonexistent plan ID returns 404."""
    user = create_test_user(db_session)
    response = client.post(
        "/api/v1/memberships/subscribe",
        json={"plan_id": str(uuid.uuid4())},
        headers=auth_headers(user.id),
    )
    assert response.status_code == 404


def test_subscribe_to_inactive_plan(client: TestClient, db_session: Session):
    """Subscribing to inactive plan returns 400 Bad Request."""
    creator = create_test_user(db_session)
    user = create_test_user(db_session)
    plan = MembershipPlan(creator_id=creator.id, name="Old Plan", monthly_price=0.0, is_active=False)
    db_session.add(plan)
    db_session.commit()

    response = client.post(
        "/api/v1/memberships/subscribe",
        json={"plan_id": plan.id},
        headers=auth_headers(user.id),
    )
    assert response.status_code == 400
    assert "Membership plan is inactive" in response.json()["detail"]


def test_creator_cannot_subscribe_to_own_plan(client: TestClient, db_session: Session):
    """Creator attempting to subscribe to their own plan returns 400."""
    creator = create_test_user(db_session, username="self_subscriber")
    plan = MembershipPlan(creator_id=creator.id, name="Self Plan", monthly_price=0.0)
    db_session.add(plan)
    db_session.commit()

    response = client.post(
        "/api/v1/memberships/subscribe",
        json={"plan_id": plan.id},
        headers=auth_headers(creator.id),
    )
    assert response.status_code == 400
    assert "Creators cannot subscribe to their own membership plans" in response.json()["detail"]


# ============================================================================
# 6. Rejection of Duplicate Active Subscriptions
# ============================================================================

def test_duplicate_active_subscription_rejected(client: TestClient, db_session: Session):
    """Rejection of duplicate active subscriptions for the same user and plan."""
    creator = create_test_user(db_session, username="dup_creator")
    subscriber = create_test_user(db_session, username="dup_sub")

    plan = MembershipPlan(creator_id=creator.id, name="Dup Test Plan", monthly_price=0.0)
    db_session.add(plan)
    db_session.commit()

    # First subscription - success
    res1 = client.post(
        "/api/v1/memberships/subscribe",
        json={"plan_id": plan.id},
        headers=auth_headers(subscriber.id),
    )
    assert res1.status_code == 201

    # Second subscription - duplicate rejection
    res2 = client.post(
        "/api/v1/memberships/subscribe",
        json={"plan_id": plan.id},
        headers=auth_headers(subscriber.id),
    )
    assert res2.status_code == 400
    assert "already have an active subscription" in res2.json()["detail"]


# ============================================================================
# 7. User Viewing Subscriptions (GET /api/v1/memberships/my)
# ============================================================================

def test_get_my_subscriptions(client: TestClient, db_session: Session):
    """User views all active and past memberships with plan details."""
    creator1 = create_test_user(db_session, username="channel_1")
    creator2 = create_test_user(db_session, username="channel_2")
    user = create_test_user(db_session, username="avid_supporter")

    plan1 = MembershipPlan(creator_id=creator1.id, name="Channel 1 Pass", monthly_price=0.0)
    plan2 = MembershipPlan(creator_id=creator2.id, name="Channel 2 Pass", monthly_price=0.0)
    db_session.add_all([plan1, plan2])
    db_session.commit()

    # Subscribe to both
    client.post("/api/v1/memberships/subscribe", json={"plan_id": plan1.id}, headers=auth_headers(user.id))
    client.post("/api/v1/memberships/subscribe", json={"plan_id": plan2.id}, headers=auth_headers(user.id))

    # Fetch user's subscriptions
    response = client.get("/api/v1/memberships/my", headers=auth_headers(user.id))
    assert response.status_code == 200
    subs = response.json()
    assert len(subs) == 2
    plan_names = [s["plan"]["name"] for s in subs]
    assert "Channel 1 Pass" in plan_names
    assert "Channel 2 Pass" in plan_names


def test_get_my_subscriptions_empty(client: TestClient, db_session: Session):
    """User with no subscriptions returns empty list."""
    user = create_test_user(db_session, username="zero_subs_user")
    response = client.get("/api/v1/memberships/my", headers=auth_headers(user.id))
    assert response.status_code == 200
    assert response.json() == []


def test_get_my_subscriptions_unauthenticated(client: TestClient):
    """Unauthenticated request to /my returns 401."""
    response = client.get("/api/v1/memberships/my")
    assert response.status_code == 401


# ============================================================================
# 8. Subscription Cancellation Flow (POST /api/v1/memberships/{id}/cancel)
# ============================================================================

def test_cancel_subscription_success(client: TestClient, db_session: Session):
    """Subscriber cancels an active subscription."""
    creator = create_test_user(db_session, username="cancel_creator")
    subscriber = create_test_user(db_session, username="cancel_sub")

    plan = MembershipPlan(creator_id=creator.id, name="Cancel Plan", monthly_price=0.0)
    db_session.add(plan)
    db_session.commit()

    sub_res = client.post(
        "/api/v1/memberships/subscribe",
        json={"plan_id": plan.id},
        headers=auth_headers(subscriber.id),
    )
    sub_id = sub_res.json()["id"]

    # Cancel subscription
    cancel_res = client.post(
        f"/api/v1/memberships/{sub_id}/cancel",
        headers=auth_headers(subscriber.id),
    )
    assert cancel_res.status_code == 200
    data = cancel_res.json()
    assert data["id"] == sub_id
    assert data["status"] == "CANCELLED"


def test_cancel_already_cancelled_subscription_rejected(client: TestClient, db_session: Session):
    """Cancelling a subscription that is already cancelled returns 400."""
    creator = create_test_user(db_session)
    subscriber = create_test_user(db_session)

    plan = MembershipPlan(creator_id=creator.id, name="Double Cancel", monthly_price=0.0)
    db_session.add(plan)
    db_session.commit()

    sub_res = client.post(
        "/api/v1/memberships/subscribe",
        json={"plan_id": plan.id},
        headers=auth_headers(subscriber.id),
    )
    sub_id = sub_res.json()["id"]

    # First cancel
    client.post(f"/api/v1/memberships/{sub_id}/cancel", headers=auth_headers(subscriber.id))

    # Second cancel
    res2 = client.post(f"/api/v1/memberships/{sub_id}/cancel", headers=auth_headers(subscriber.id))
    assert res2.status_code == 400
    assert "already cancelled" in res2.json()["detail"]


def test_cancel_subscription_unauthorized_user(client: TestClient, db_session: Session):
    """User B cannot cancel User A's subscription."""
    creator = create_test_user(db_session)
    user_a = create_test_user(db_session, username="user_a")
    user_b = create_test_user(db_session, username="user_b")

    plan = MembershipPlan(creator_id=creator.id, name="Guarded Plan", monthly_price=0.0)
    db_session.add(plan)
    db_session.commit()

    sub_res = client.post(
        "/api/v1/memberships/subscribe",
        json={"plan_id": plan.id},
        headers=auth_headers(user_a.id),
    )
    sub_id = sub_res.json()["id"]

    # user_b attempts to cancel user_a's subscription
    res = client.post(
        f"/api/v1/memberships/{sub_id}/cancel",
        headers=auth_headers(user_b.id),
    )
    assert res.status_code == 403


def test_cancel_subscription_not_found(client: TestClient, db_session: Session):
    """Cancelling a non-existent subscription ID returns 404."""
    user = create_test_user(db_session)
    res = client.post(
        f"/api/v1/memberships/{str(uuid.uuid4())}/cancel",
        headers=auth_headers(user.id),
    )
    assert res.status_code == 404


def test_resubscribe_after_cancellation(client: TestClient, db_session: Session):
    """After cancelling a subscription, user can seamlessly re-subscribe to the same plan."""
    creator = create_test_user(db_session, username="resub_creator")
    subscriber = create_test_user(db_session, username="resub_user")

    plan = MembershipPlan(creator_id=creator.id, name="Re-sub Plan", monthly_price=0.0)
    db_session.add(plan)
    db_session.commit()

    # Initial subscription
    sub_res = client.post(
        "/api/v1/memberships/subscribe",
        json={"plan_id": plan.id},
        headers=auth_headers(subscriber.id),
    )
    sub_id = sub_res.json()["id"]

    # Cancel
    client.post(f"/api/v1/memberships/{sub_id}/cancel", headers=auth_headers(subscriber.id))

    # Re-subscribe
    resub_res = client.post(
        "/api/v1/memberships/subscribe",
        json={"plan_id": plan.id},
        headers=auth_headers(subscriber.id),
    )
    assert resub_res.status_code == 201
    assert resub_res.json()["status"] == "ACTIVE"


# ============================================================================
# 9. Plan Management (Update & Deactivate Permissions)
# ============================================================================

def test_creator_update_own_plan(client: TestClient, db_session: Session):
    """Creator can update their own membership plan."""
    creator = create_test_user(db_session, username="updating_creator")
    plan = MembershipPlan(
        creator_id=creator.id,
        name="Original Name",
        description="Original Desc",
        monthly_price=0.0,
        benefits=["Old Benefit"],
    )
    db_session.add(plan)
    db_session.commit()

    response = client.patch(
        f"/api/v1/memberships/plans/{plan.id}",
        json={
            "name": "Updated Name",
            "description": "Updated Description",
            "benefits": ["New Benefit 1", "New Benefit 2"],
        },
        headers=auth_headers(creator.id),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["description"] == "Updated Description"
    assert data["benefits"] == ["New Benefit 1", "New Benefit 2"]


def test_non_creator_cannot_update_plan(client: TestClient, db_session: Session):
    """Non-creator attempting to update a plan receives 403 Forbidden."""
    creator = create_test_user(db_session, username="legit_owner")
    imposter = create_test_user(db_session, username="imposter_user")

    plan = MembershipPlan(creator_id=creator.id, name="Protected Plan", monthly_price=0.0)
    db_session.add(plan)
    db_session.commit()

    response = client.patch(
        f"/api/v1/memberships/plans/{plan.id}",
        json={"name": "Hacked Plan"},
        headers=auth_headers(imposter.id),
    )
    assert response.status_code == 403


def test_creator_deactivate_own_plan(client: TestClient, db_session: Session):
    """Creator deactivates their own plan."""
    creator = create_test_user(db_session, username="deactivating_creator")
    plan = MembershipPlan(creator_id=creator.id, name="To Deactivate", monthly_price=0.0, is_active=True)
    db_session.add(plan)
    db_session.commit()

    response = client.delete(
        f"/api/v1/memberships/plans/{plan.id}",
        headers=auth_headers(creator.id),
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Membership plan deactivated successfully."

    # Verify plan is inactive
    db_session.refresh(plan)
    assert plan.is_active is False


def test_non_creator_cannot_deactivate_plan(client: TestClient, db_session: Session):
    """Non-creator attempting to delete a plan receives 403 Forbidden."""
    creator = create_test_user(db_session, username="owner_deact")
    stranger = create_test_user(db_session, username="stranger_deact")

    plan = MembershipPlan(creator_id=creator.id, name="Safe Plan", monthly_price=0.0, is_active=True)
    db_session.add(plan)
    db_session.commit()

    response = client.delete(
        f"/api/v1/memberships/plans/{plan.id}",
        headers=auth_headers(stranger.id),
    )
    assert response.status_code == 403
    db_session.refresh(plan)
    assert plan.is_active is True


# ============================================================================
# 10. Adversarial & Edge Case Verification
# ============================================================================

def test_db_constraints_enforce_unique_active_subscription(db_session: Session):
    """Database partial unique index enforces uniqueness for active subscriptions."""
    creator = create_test_user(db_session, username="db_uniq_creator")
    subscriber = create_test_user(db_session, username="db_uniq_sub")

    plan = MembershipPlan(
        creator_id=creator.id,
        name="DB Index Test Plan",
        monthly_price=0.0,
        tier_type=MembershipTierType.FREE,
        is_active=True,
    )
    db_session.add(plan)
    db_session.commit()

    now = datetime.now(timezone.utc)
    # First ACTIVE subscription
    sub1 = Subscription(
        plan_id=plan.id,
        user_id=subscriber.id,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
    )
    db_session.add(sub1)
    db_session.commit()

    # Second ACTIVE subscription for same user and plan must fail with IntegrityError
    sub2 = Subscription(
        plan_id=plan.id,
        user_id=subscriber.id,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
    )
    db_session.add(sub2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # However, cancelling sub1 and adding a new ACTIVE subscription must succeed
    sub1.status = SubscriptionStatus.CANCELLED
    db_session.commit()

    sub3 = Subscription(
        plan_id=plan.id,
        user_id=subscriber.id,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
    )
    db_session.add(sub3)
    db_session.commit()
    assert sub3.id is not None


def test_cancel_subscription_via_plan_id(client: TestClient, db_session: Session):
    """Subscriber can cancel their active subscription by passing plan_id to /{id}/cancel."""
    creator = create_test_user(db_session, username="cancel_planid_creator")
    subscriber = create_test_user(db_session, username="cancel_planid_sub")

    plan = MembershipPlan(creator_id=creator.id, name="Cancel PlanId", monthly_price=0.0)
    db_session.add(plan)
    db_session.commit()

    # Subscribe
    res_sub = client.post(
        "/api/v1/memberships/subscribe",
        json={"plan_id": plan.id},
        headers=auth_headers(subscriber.id),
    )
    assert res_sub.status_code == 201

    # Cancel passing plan_id
    res_cancel = client.post(
        f"/api/v1/memberships/{plan.id}/cancel",
        headers=auth_headers(subscriber.id),
    )
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == "CANCELLED"

    # Cancelling again via plan_id must return 400 "already cancelled"
    res_cancel2 = client.post(
        f"/api/v1/memberships/{plan.id}/cancel",
        headers=auth_headers(subscriber.id),
    )
    assert res_cancel2.status_code == 400
    assert "already cancelled" in res_cancel2.json()["detail"]


def test_creator_can_cancel_member_subscription(client: TestClient, db_session: Session):
    """Plan creator can cancel a subscriber's subscription."""
    creator = create_test_user(db_session, username="admin_creator")
    subscriber = create_test_user(db_session, username="expelled_sub")

    plan = MembershipPlan(creator_id=creator.id, name="Creator Guarded Plan", monthly_price=0.0)
    db_session.add(plan)
    db_session.commit()

    res_sub = client.post(
        "/api/v1/memberships/subscribe",
        json={"plan_id": plan.id},
        headers=auth_headers(subscriber.id),
    )
    sub_id = res_sub.json()["id"]

    # Creator cancels member's subscription
    res_cancel = client.post(
        f"/api/v1/memberships/{sub_id}/cancel",
        headers=auth_headers(creator.id),
    )
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == "CANCELLED"


def test_update_plan_reject_paid_when_flag_disabled(client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch):
    """Creator cannot update plan to VIP or price > 0 when ENABLE_PAID_MEMBERSHIPS is False."""
    monkeypatch.setattr(settings, "ENABLE_PAID_MEMBERSHIPS", False)
    creator = create_test_user(db_session, username="patch_creator")

    plan = MembershipPlan(creator_id=creator.id, name="Free to Paid Attempt", monthly_price=0.0, tier_type=MembershipTierType.FREE)
    db_session.add(plan)
    db_session.commit()

    # Attempt to change price to 199.0
    res_price = client.patch(
        f"/api/v1/memberships/plans/{plan.id}",
        json={"monthly_price": 199.0},
        headers=auth_headers(creator.id),
    )
    assert res_price.status_code == 400
    assert "Paid VIP memberships are currently disabled" in res_price.json()["detail"]

    # Attempt to change tier to VIP
    res_tier = client.patch(
        f"/api/v1/memberships/plans/{plan.id}",
        json={"tier_type": "VIP"},
        headers=auth_headers(creator.id),
    )
    assert res_tier.status_code == 400
    assert "Paid VIP memberships are currently disabled" in res_tier.json()["detail"]


def test_free_tier_with_nonzero_price_rejected(client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch):
    """Even if paid flag is enabled, a FREE tier cannot have a monthly_price > 0."""
    monkeypatch.setattr(settings, "ENABLE_PAID_MEMBERSHIPS", True)
    creator = create_test_user(db_session, username="free_tier_checker")

    # Creating FREE tier with price > 0
    res_create = client.post(
        "/api/v1/memberships/plans",
        json={"name": "Bad Free Plan", "tier_type": "FREE", "monthly_price": 99.0},
        headers=auth_headers(creator.id),
    )
    assert res_create.status_code == 400
    assert "Free tier plans must have a monthly price of 0.0" in res_create.json()["detail"]

    # Existing FREE plan updating to price > 0
    valid_plan = MembershipPlan(creator_id=creator.id, name="Valid Free Plan", monthly_price=0.0, tier_type=MembershipTierType.FREE)
    db_session.add(valid_plan)
    db_session.commit()

    res_patch = client.patch(
        f"/api/v1/memberships/plans/{valid_plan.id}",
        json={"monthly_price": 99.0},
        headers=auth_headers(creator.id),
    )
    assert res_patch.status_code == 400
    assert "Free tier plans must have a monthly price of 0.0" in res_patch.json()["detail"]


def test_get_single_inactive_plan_hidden_from_public(client: TestClient, db_session: Session):
    """Public user requesting single inactive plan gets 404, but creator gets 200."""
    creator = create_test_user(db_session, username="inactive_plan_author")
    stranger = create_test_user(db_session, username="inactive_plan_viewer")

    plan = MembershipPlan(creator_id=creator.id, name="Retired Plan", monthly_price=0.0, is_active=False)
    db_session.add(plan)
    db_session.commit()

    # Anonymous user
    res_anon = client.get(f"/api/v1/memberships/plans/{plan.id}")
    assert res_anon.status_code == 404

    # Stranger user
    res_stranger = client.get(f"/api/v1/memberships/plans/{plan.id}", headers=auth_headers(stranger.id))
    assert res_stranger.status_code == 404

    # Creator themselves can see it
    res_creator = client.get(f"/api/v1/memberships/plans/{plan.id}", headers=auth_headers(creator.id))
    assert res_creator.status_code == 200
    assert res_creator.json()["name"] == "Retired Plan"
    assert res_creator.json()["is_active"] is False


def test_subscribe_to_deactivated_creator_rejected(client: TestClient, db_session: Session):
    """Subscribing to a plan whose creator account has been deactivated is rejected."""
    creator = create_test_user(db_session, username="banned_creator", is_active=True)
    plan = MembershipPlan(creator_id=creator.id, name="Banned Plan", monthly_price=0.0, is_active=True)
    db_session.add(plan)
    db_session.commit()

    # Deactivate creator account
    creator.is_active = False
    db_session.commit()

    subscriber = create_test_user(db_session, username="banned_sub")
    res = client.post(
        "/api/v1/memberships/subscribe",
        json={"plan_id": plan.id},
        headers=auth_headers(subscriber.id),
    )
    assert res.status_code == 400
    assert "Creator account is deactivated" in res.json()["detail"]


def test_plans_list_excludes_deactivated_creator(client: TestClient, db_session: Session):
    """Public plan listing excludes plans created by deactivated creators."""
    active_creator = create_test_user(db_session, username="active_creator_plans")
    deact_creator = create_test_user(db_session, username="deact_creator_plans")

    p1 = MembershipPlan(creator_id=active_creator.id, name="Visible Plan", monthly_price=0.0, is_active=True)
    p2 = MembershipPlan(creator_id=deact_creator.id, name="Invisible Plan", monthly_price=0.0, is_active=True)
    db_session.add_all([p1, p2])
    db_session.commit()

    deact_creator.is_active = False
    db_session.commit()

    res = client.get("/api/v1/memberships/plans")
    assert res.status_code == 200
    plan_names = [p["name"] for p in res.json()]
    assert "Visible Plan" in plan_names
    assert "Invisible Plan" not in plan_names


def test_update_and_delete_nonexistent_plan_returns_404(client: TestClient, db_session: Session):
    """PATCH and DELETE on nonexistent plan returns 404."""
    user = create_test_user(db_session)
    fake_id = str(uuid.uuid4())

    res_patch = client.patch(
        f"/api/v1/memberships/plans/{fake_id}",
        json={"name": "Ghost"},
        headers=auth_headers(user.id),
    )
    assert res_patch.status_code == 404

    res_delete = client.delete(
        f"/api/v1/memberships/plans/{fake_id}",
        headers=auth_headers(user.id),
    )
    assert res_delete.status_code == 404


def test_get_my_subscriptions_status_filter(client: TestClient, db_session: Session):
    """Filter /my subscriptions by status (ACTIVE vs CANCELLED)."""
    creator1 = create_test_user(db_session, username="creator_filter_1")
    creator2 = create_test_user(db_session, username="creator_filter_2")
    user = create_test_user(db_session, username="filtering_user")

    p1 = MembershipPlan(creator_id=creator1.id, name="Active Target Plan", monthly_price=0.0)
    p2 = MembershipPlan(creator_id=creator2.id, name="Cancelled Target Plan", monthly_price=0.0)
    db_session.add_all([p1, p2])
    db_session.commit()

    # Subscribe to both
    res1 = client.post("/api/v1/memberships/subscribe", json={"plan_id": p1.id}, headers=auth_headers(user.id))
    res2 = client.post("/api/v1/memberships/subscribe", json={"plan_id": p2.id}, headers=auth_headers(user.id))
    sub2_id = res2.json()["id"]

    # Cancel p2
    client.post(f"/api/v1/memberships/{sub2_id}/cancel", headers=auth_headers(user.id))

    # Query all
    res_all = client.get("/api/v1/memberships/my", headers=auth_headers(user.id))
    assert res_all.status_code == 200
    assert len(res_all.json()) == 2

    # Query active only
    res_active = client.get("/api/v1/memberships/my?status=ACTIVE", headers=auth_headers(user.id))
    assert res_active.status_code == 200
    assert len(res_active.json()) == 1
    assert res_active.json()[0]["plan"]["name"] == "Active Target Plan"

    # Query cancelled only
    res_canc = client.get("/api/v1/memberships/my?status=CANCELLED", headers=auth_headers(user.id))
    assert res_canc.status_code == 200
    assert len(res_canc.json()) == 1
    assert res_canc.json()[0]["plan"]["name"] == "Cancelled Target Plan"


def test_vip_tier_with_zero_price_rejected_when_paid_enabled(client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch):
    """When paid mode is enabled, VIP tier must have a price > 0.0."""
    monkeypatch.setattr(settings, "ENABLE_PAID_MEMBERSHIPS", True)
    creator = create_test_user(db_session, username="vip_zero_checker")
    res = client.post(
        "/api/v1/memberships/plans",
        json={"name": "Zero VIP Plan", "tier_type": "VIP", "monthly_price": 0.0},
        headers=auth_headers(creator.id),
    )
    assert res.status_code == 400
    assert "VIP tier plans must have a monthly price greater than 0.0" in res.json()["detail"]


def test_resubscription_preserves_past_history_in_my_memberships(client: TestClient, db_session: Session):
    """Resubscribing after cancellation preserves the previous cancelled record in /my history."""
    creator = create_test_user(db_session, username="history_creator")
    subscriber = create_test_user(db_session, username="history_sub")

    plan = MembershipPlan(creator_id=creator.id, name="History Pass", monthly_price=0.0)
    db_session.add(plan)
    db_session.commit()

    # 1. Subscribe
    res1 = client.post("/api/v1/memberships/subscribe", json={"plan_id": plan.id}, headers=auth_headers(subscriber.id))
    assert res1.status_code == 201
    sub1_id = res1.json()["id"]

    # 2. Cancel
    client.post(f"/api/v1/memberships/{sub1_id}/cancel", headers=auth_headers(subscriber.id))

    # 3. Resubscribe
    res2 = client.post("/api/v1/memberships/subscribe", json={"plan_id": plan.id}, headers=auth_headers(subscriber.id))
    assert res2.status_code == 201
    sub2_id = res2.json()["id"]
    assert sub2_id != sub1_id

    # 4. GET /my shows 2 records: 1 ACTIVE, 1 CANCELLED
    all_res = client.get("/api/v1/memberships/my", headers=auth_headers(subscriber.id))
    assert all_res.status_code == 200
    items = all_res.json()
    assert len(items) == 2
    statuses = [item["status"] for item in items]
    assert "ACTIVE" in statuses
    assert "CANCELLED" in statuses


def test_delete_plan_deactivated_account_service_level(db_session: Session):
    """Direct service call delete_plan rejects deactivated creator with PermissionError."""
    creator = create_test_user(db_session, is_active=True)
    plan = MembershipPlan(creator_id=creator.id, name="Deact Delete Plan", monthly_price=0.0)
    db_session.add(plan)
    db_session.commit()

    creator.is_active = False
    db_session.commit()

    service = MembershipService(db_session)
    with pytest.raises(PermissionError):
        service.delete_plan(plan_id=plan.id, creator_id=creator.id)


def test_cancel_expired_subscription_rejected(client: TestClient, db_session: Session):
    """Attempting to cancel an expired subscription is rejected and does not mutate status."""
    creator = create_test_user(db_session, username="expired_creator")
    subscriber = create_test_user(db_session, username="expired_sub")

    plan = MembershipPlan(creator_id=creator.id, name="Expired Guard Plan", monthly_price=0.0)
    db_session.add(plan)
    db_session.commit()

    now = datetime.now(timezone.utc)
    expired_sub = Subscription(
        plan_id=plan.id,
        user_id=subscriber.id,
        status=SubscriptionStatus.EXPIRED,
        current_period_start=now - timedelta(days=60),
        current_period_end=now - timedelta(days=30),
    )
    db_session.add(expired_sub)
    db_session.commit()
    db_session.refresh(expired_sub)

    # Attempt to cancel expired subscription
    res = client.post(
        f"/api/v1/memberships/{expired_sub.id}/cancel",
        headers=auth_headers(subscriber.id),
    )
    assert res.status_code == 400
    assert "Subscription has expired" in res.json()["detail"]

    # Verify status is still EXPIRED (not mutated to CANCELLED)
    db_session.refresh(expired_sub)
    assert expired_sub.status == SubscriptionStatus.EXPIRED


def test_update_plan_currency_empty_whitespace_rejected(client: TestClient, db_session: Session):
    """Updating plan currency with whitespace-only string fails with 422."""
    creator = create_test_user(db_session, username="curr_clean_creator")
    plan = MembershipPlan(creator_id=creator.id, name="Curr Clean Plan", monthly_price=0.0)
    db_session.add(plan)
    db_session.commit()

    res = client.patch(
        f"/api/v1/memberships/plans/{plan.id}",
        json={"currency": "   "},
        headers=auth_headers(creator.id),
    )
    assert res.status_code == 422


def test_subscribe_nonexistent_user_service_level(db_session: Session):
    """Direct service call to subscribe with nonexistent user raises LookupError."""
    creator = create_test_user(db_session)
    plan = MembershipPlan(creator_id=creator.id, name="Nonexistent User Plan", monthly_price=0.0)
    db_session.add(plan)
    db_session.commit()

    service = MembershipService(db_session)
    with pytest.raises(LookupError, match="User not found"):
        service.subscribe(user_id=str(uuid.uuid4()), plan_id=plan.id)


def test_create_plan_nonexistent_creator_service_level(db_session: Session):
    """Direct service call to create_plan with nonexistent creator raises LookupError."""
    service = MembershipService(db_session)
    payload = CreateMembershipPlanRequest(name="Ghost Creator Plan")
    with pytest.raises(LookupError, match="Creator not found"):
        service.create_plan(creator_id=str(uuid.uuid4()), payload=payload)


def test_controller_sanitizes_integrity_error_on_subscribe(monkeypatch: pytest.MonkeyPatch, db_session: Session):
    """MembershipController.subscribe catches IntegrityError and sanitizes raw SQL leaks."""
    creator = create_test_user(db_session, username="mock_sub_creator")
    subscriber = create_test_user(db_session, username="mock_sub_user")
    plan = MembershipPlan(creator_id=creator.id, name="Mock Integrity Plan", monthly_price=0.0)
    db_session.add(plan)
    db_session.commit()

    def mock_subscribe_raising_integrity(*args, **kwargs):
        raise IntegrityError("INSERT INTO subscriptions ... UNIQUE constraint failed", None, None)

    monkeypatch.setattr(MembershipService, "subscribe", mock_subscribe_raising_integrity)

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        MembershipController.subscribe(
            current_user=subscriber,
            payload=SubscribeMembershipRequest(plan_id=plan.id),
            db=db_session,
        )
    assert exc_info.value.status_code == 400
    assert "INSERT INTO" not in exc_info.value.detail
    assert exc_info.value.detail == "You already have an active subscription to this plan."


def test_cancel_subscription_service_level_expired_rejected(db_session: Session):
    """Direct service call cancel_subscription on expired subscription raises ValueError."""
    creator = create_test_user(db_session)
    subscriber = create_test_user(db_session)
    plan = MembershipPlan(creator_id=creator.id, name="Service Expired Plan", monthly_price=0.0)
    db_session.add(plan)
    db_session.commit()

    now = datetime.now(timezone.utc)
    expired_sub = Subscription(
        plan_id=plan.id,
        user_id=subscriber.id,
        status=SubscriptionStatus.EXPIRED,
        current_period_start=now - timedelta(days=60),
        current_period_end=now - timedelta(days=30),
    )
    db_session.add(expired_sub)
    db_session.commit()

    service = MembershipService(db_session)
    with pytest.raises(ValueError, match="Subscription has expired"):
        service.cancel_subscription(subscription_id=expired_sub.id, user_id=subscriber.id)



