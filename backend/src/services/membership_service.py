from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from src.config.settings import settings
from src.models.membership import (
    MembershipPlan,
    MembershipTierType,
    Subscription,
    SubscriptionStatus,
)
from src.models.user import User
from src.repositories.membership_repository import (
    MembershipPlanRepository,
    SubscriptionRepository,
)
from src.validations.membership_schemas import (
    CreateMembershipPlanRequest,
    UpdateMembershipPlanRequest,
)


class MembershipService:
    def __init__(self, db: Session):
        self.db = db
        self.plan_repo = MembershipPlanRepository(db)
        self.sub_repo = SubscriptionRepository(db)

    def create_plan(self, creator_id: str, payload: CreateMembershipPlanRequest) -> MembershipPlan:
        user = self.db.query(User).filter(User.id == creator_id).first()
        if not user:
            raise LookupError("Creator not found.")
        if not user.is_active:
            raise PermissionError("User account is deactivated.")

        # Business Rule R1: Feature toggle ENABLE_PAID_MEMBERSHIPS
        paid_enabled = getattr(settings, "ENABLE_PAID_MEMBERSHIPS", False)

        name = payload.name.strip() if payload.name else ""
        if not name:
            raise ValueError("Plan name cannot be empty.")

        price = payload.monthly_price if payload.monthly_price is not None else 0.0
        tier = payload.tier_type or MembershipTierType.FREE

        if not paid_enabled:
            # VIP paid tiers are hidden/restricted from public creation until explicitly enabled
            if tier == MembershipTierType.VIP or price > 0.0:
                raise ValueError("Paid VIP memberships are currently disabled. Only ₹0 Free plans are allowed.")
            price = 0.0
            tier = MembershipTierType.FREE

        if price < 0.0:
            raise ValueError("Monthly price must be non-negative.")

        if tier == MembershipTierType.FREE and price > 0.0:
            raise ValueError("Free tier plans must have a monthly price of 0.0.")

        if paid_enabled and tier == MembershipTierType.VIP and price <= 0.0:
            raise ValueError("VIP tier plans must have a monthly price greater than 0.0.")

        benefits = [str(b).strip() for b in (payload.benefits or []) if str(b).strip()]
        desc = payload.description.strip() if payload.description and payload.description.strip() else None
        currency = payload.currency.strip().upper() if payload.currency and payload.currency.strip() else "INR"

        plan = MembershipPlan(
            creator_id=creator_id,
            name=name,
            description=desc,
            monthly_price=price,
            currency=currency,
            tier_type=tier,
            benefits=benefits,
            is_active=True if payload.is_active is None else payload.is_active,
        )
        return self.plan_repo.create(plan)

    def list_plans(
        self,
        creator_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[MembershipPlan]:
        if creator_id is not None:
            creator_id = creator_id.strip()
            if not creator_id:
                creator_id = None
        paid_enabled = getattr(settings, "ENABLE_PAID_MEMBERSHIPS", False)
        return self.plan_repo.get_active_plans(
            creator_id=creator_id,
            allow_paid=paid_enabled,
            skip=skip,
            limit=limit,
        )

    def get_plan(self, plan_id: str, requesting_user: Optional[User] = None) -> MembershipPlan:
        plan = self.plan_repo.get_by_id(plan_id)
        if not plan:
            raise LookupError("Membership plan not found.")

        # If creator is inactive, hide plan from non-creator viewers
        if not plan.creator or not plan.creator.is_active:
            if not requesting_user or requesting_user.id != plan.creator_id:
                raise LookupError("Membership plan not found.")

        # Inactive plans are only viewable by their creator
        if not plan.is_active:
            if not requesting_user or requesting_user.id != plan.creator_id:
                raise LookupError("Membership plan not found.")

        paid_enabled = getattr(settings, "ENABLE_PAID_MEMBERSHIPS", False)
        if not paid_enabled and (plan.tier_type == MembershipTierType.VIP or plan.monthly_price > 0.0):
            # Only the creator may view their own unpublished/restricted VIP plan
            if not requesting_user or requesting_user.id != plan.creator_id:
                raise LookupError("Membership plan not found.")

        return plan

    def update_plan(
        self,
        plan_id: str,
        creator_id: str,
        payload: UpdateMembershipPlanRequest,
    ) -> MembershipPlan:
        plan = self.plan_repo.get_by_id(plan_id)
        if not plan:
            raise LookupError("Membership plan not found.")

        # Business Rule: Creators can only manage their own membership plans
        if plan.creator_id != creator_id:
            raise PermissionError("You can only manage your own membership plans.")

        user = self.db.query(User).filter(User.id == creator_id).first()
        if not user:
            raise LookupError("Creator not found.")
        if not user.is_active:
            raise PermissionError("User account is deactivated.")

        paid_enabled = getattr(settings, "ENABLE_PAID_MEMBERSHIPS", False)

        if payload.name is not None:
            clean_name = payload.name.strip()
            if not clean_name:
                raise ValueError("Plan name cannot be empty.")
            plan.name = clean_name
        if payload.description is not None:
            plan.description = payload.description.strip() if payload.description.strip() else None
        if payload.benefits is not None:
            plan.benefits = [str(b).strip() for b in payload.benefits if str(b).strip()]
        if payload.is_active is not None:
            plan.is_active = payload.is_active

        if payload.tier_type is not None or payload.monthly_price is not None:
            target_tier = payload.tier_type if payload.tier_type is not None else plan.tier_type
            target_price = payload.monthly_price if payload.monthly_price is not None else plan.monthly_price
            if not paid_enabled and (target_tier == MembershipTierType.VIP or target_price > 0.0):
                raise ValueError("Paid VIP memberships are currently disabled.")
            if target_price < 0.0:
                raise ValueError("Monthly price must be non-negative.")
            if target_tier == MembershipTierType.FREE and target_price > 0.0:
                raise ValueError("Free tier plans must have a monthly price of 0.0.")
            if paid_enabled and target_tier == MembershipTierType.VIP and target_price <= 0.0:
                raise ValueError("VIP tier plans must have a monthly price greater than 0.0.")
            plan.tier_type = target_tier
            plan.monthly_price = target_price

        if payload.currency is not None:
            clean_curr = payload.currency.strip().upper()
            if not clean_curr:
                raise ValueError("Currency cannot be empty.")
            plan.currency = clean_curr

        plan.updated_at = datetime.now(timezone.utc)
        return self.plan_repo.update(plan)

    def delete_plan(self, plan_id: str, creator_id: str) -> None:
        plan = self.plan_repo.get_by_id(plan_id)
        if not plan:
            raise LookupError("Membership plan not found.")
        if plan.creator_id != creator_id:
            raise PermissionError("You can only manage your own membership plans.")
        user = self.db.query(User).filter(User.id == creator_id).first()
        if not user:
            raise LookupError("Creator not found.")
        if not user.is_active:
            raise PermissionError("User account is deactivated.")
        plan.is_active = False
        plan.updated_at = datetime.now(timezone.utc)
        self.plan_repo.update(plan)

    def subscribe(self, user_id: str, plan_id: str) -> Subscription:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise LookupError("User not found.")
        if not user.is_active:
            raise PermissionError("User account is deactivated.")

        plan = self.plan_repo.get_by_id(plan_id)
        if not plan:
            raise LookupError("Membership plan not found.")
        if not plan.is_active:
            raise ValueError("Membership plan is inactive.")
        if not plan.creator or not plan.creator.is_active:
            raise ValueError("Creator account is deactivated.")

        # Business Rule: Cannot subscribe to own plan
        if plan.creator_id == user_id:
            raise ValueError("Creators cannot subscribe to their own membership plans.")

        paid_enabled = getattr(settings, "ENABLE_PAID_MEMBERSHIPS", False)
        if not paid_enabled and (plan.tier_type == MembershipTierType.VIP or plan.monthly_price > 0.0):
            raise ValueError("Paid VIP memberships are currently disabled.")

        # Business Rule: Rejection of duplicate active subscriptions for the same user and plan
        active_sub = self.sub_repo.get_active_subscription(user_id=user_id, plan_id=plan_id)
        if active_sub:
            raise ValueError("You already have an active subscription to this plan.")

        now = datetime.now(timezone.utc)
        renewal_end = now + timedelta(days=30)

        # Create new ACTIVE subscription (preserves past history for /my endpoint)
        new_sub = Subscription(
            plan_id=plan_id,
            user_id=user_id,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=now,
            current_period_end=renewal_end,
            created_at=now,
            updated_at=now,
        )
        created = self.sub_repo.create(new_sub)
        created.plan = plan
        return created

    def get_my_subscriptions(
        self,
        user_id: str,
        status: Optional[SubscriptionStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Subscription]:
        return self.sub_repo.get_user_subscriptions(
            user_id=user_id,
            status=status,
            skip=skip,
            limit=limit,
        )

    def cancel_subscription(self, subscription_id: str, user_id: str) -> Subscription:
        sub = self.sub_repo.get_by_id(subscription_id)
        if not sub:
            # Fallback: check if caller passed plan_id instead of subscription_id
            sub = self.sub_repo.get_subscription_by_user_and_plan(user_id=user_id, plan_id=subscription_id)
        if not sub:
            raise LookupError("Subscription not found.")

        # Verify permissions: only the subscriber or the plan creator can cancel
        plan_creator_id = sub.plan.creator_id if sub.plan else None
        if not plan_creator_id and sub.plan_id:
            plan_obj = self.plan_repo.get_by_id(sub.plan_id)
            if plan_obj:
                sub.plan = plan_obj
                plan_creator_id = plan_obj.creator_id

        if sub.user_id != user_id and plan_creator_id != user_id:
            raise PermissionError("You do not have permission to cancel this subscription.")

        if sub.status == SubscriptionStatus.CANCELLED:
            raise ValueError("Subscription is already cancelled.")
        if sub.status == SubscriptionStatus.EXPIRED:
            raise ValueError("Subscription has expired.")
        if sub.status != SubscriptionStatus.ACTIVE:
            raise ValueError(f"Subscription is not active (status: {sub.status.value}).")

        plan_cache = sub.plan
        sub.status = SubscriptionStatus.CANCELLED
        sub.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(sub)
        if plan_cache is not None:
            sub.plan = plan_cache
        return sub
