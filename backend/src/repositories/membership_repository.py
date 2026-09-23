from typing import List, Optional
from sqlalchemy.orm import Session, joinedload, selectinload
from src.models.membership import (
    MembershipPlan,
    MembershipTierType,
    Subscription,
    SubscriptionStatus,
)
from src.models.user import User
from src.repositories.base_repository import BaseRepository


class MembershipPlanRepository(BaseRepository[MembershipPlan]):
    def __init__(self, db: Session):
        super().__init__(MembershipPlan, db)

    def get_by_id(self, id: str) -> Optional[MembershipPlan]:
        return (
            self.db.query(MembershipPlan)
            .options(
                joinedload(MembershipPlan.creator).joinedload(User.profile),
                selectinload(MembershipPlan.subscriptions),
            )
            .filter(MembershipPlan.id == id)
            .first()
        )

    def get_active_plans(
        self,
        creator_id: Optional[str] = None,
        allow_paid: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> List[MembershipPlan]:
        query = (
            self.db.query(MembershipPlan)
            .options(
                joinedload(MembershipPlan.creator).joinedload(User.profile),
                selectinload(MembershipPlan.subscriptions),
            )
            .filter(
                MembershipPlan.is_active == True,
                MembershipPlan.creator.has(is_active=True),
            )
        )
        if creator_id is not None:
            clean_creator_id = creator_id.strip()
            if clean_creator_id:
                query = query.filter(MembershipPlan.creator_id == clean_creator_id)
        if not allow_paid:
            query = query.filter(
                MembershipPlan.tier_type == MembershipTierType.FREE,
                MembershipPlan.monthly_price == 0.0,
            )
        return (
            query.order_by(MembershipPlan.created_at.desc(), MembershipPlan.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_active_plans(
        self,
        creator_id: Optional[str] = None,
        allow_paid: bool = False,
    ) -> int:
        query = self.db.query(MembershipPlan).filter(
            MembershipPlan.is_active == True,
            MembershipPlan.creator.has(is_active=True),
        )
        if creator_id is not None:
            clean_creator_id = creator_id.strip()
            if clean_creator_id:
                query = query.filter(MembershipPlan.creator_id == clean_creator_id)
        if not allow_paid:
            query = query.filter(
                MembershipPlan.tier_type == MembershipTierType.FREE,
                MembershipPlan.monthly_price == 0.0,
            )
        return query.count()


class SubscriptionRepository(BaseRepository[Subscription]):
    def __init__(self, db: Session):
        super().__init__(Subscription, db)

    def get_by_id(self, id: str) -> Optional[Subscription]:
        return (
            self.db.query(Subscription)
            .options(
                joinedload(Subscription.plan).joinedload(MembershipPlan.creator).joinedload(User.profile),
                joinedload(Subscription.user).joinedload(User.profile),
            )
            .filter(Subscription.id == id)
            .first()
        )

    def get_active_subscription(self, user_id: str, plan_id: str) -> Optional[Subscription]:
        return (
            self.db.query(Subscription)
            .options(
                joinedload(Subscription.plan).joinedload(MembershipPlan.creator).joinedload(User.profile),
            )
            .filter(
                Subscription.user_id == user_id,
                Subscription.plan_id == plan_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
            .first()
        )

    def get_subscription_by_user_and_plan(self, user_id: str, plan_id: str) -> Optional[Subscription]:
        return (
            self.db.query(Subscription)
            .options(
                joinedload(Subscription.plan).joinedload(MembershipPlan.creator).joinedload(User.profile),
            )
            .filter(
                Subscription.user_id == user_id,
                Subscription.plan_id == plan_id,
            )
            .order_by(
                (Subscription.status == SubscriptionStatus.ACTIVE).desc(),
                Subscription.created_at.desc(),
            )
            .first()
        )

    def get_user_subscriptions(
        self,
        user_id: str,
        status: Optional[SubscriptionStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Subscription]:
        query = (
            self.db.query(Subscription)
            .options(
                joinedload(Subscription.plan).joinedload(MembershipPlan.creator).joinedload(User.profile),
            )
            .filter(Subscription.user_id == user_id)
        )
        if status is not None:
            query = query.filter(Subscription.status == status)
        return (
            query.order_by(Subscription.created_at.desc(), Subscription.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
