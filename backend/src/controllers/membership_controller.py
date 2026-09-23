from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from src.models.membership import SubscriptionStatus
from src.models.user import User
from src.services.membership_service import MembershipService
from src.validations.membership_schemas import (
    CreateMembershipPlanRequest,
    MembershipPlanResponse,
    SubscribeMembershipRequest,
    SubscriptionResponse,
    UpdateMembershipPlanRequest,
)


class MembershipController:
    @staticmethod
    def create_plan(
        current_user: User,
        payload: CreateMembershipPlanRequest,
        db: Session,
    ) -> MembershipPlanResponse:
        service = MembershipService(db)
        try:
            plan = service.create_plan(creator_id=current_user.id, payload=payload)
            return MembershipPlanResponse.from_orm_model(plan)
        except PermissionError as err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Database integrity constraint violation.",
            )
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def list_plans(
        creator_id: Optional[str],
        skip: int,
        limit: int,
        db: Session,
    ) -> List[MembershipPlanResponse]:
        service = MembershipService(db)
        plans = service.list_plans(creator_id=creator_id, skip=skip, limit=limit)
        return [MembershipPlanResponse.from_orm_model(p) for p in plans]

    @staticmethod
    def get_plan(
        plan_id: str,
        requesting_user: Optional[User],
        db: Session,
    ) -> MembershipPlanResponse:
        service = MembershipService(db)
        try:
            plan = service.get_plan(plan_id=plan_id, requesting_user=requesting_user)
            return MembershipPlanResponse.from_orm_model(plan)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except PermissionError as err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))

    @staticmethod
    def update_plan(
        plan_id: str,
        current_user: User,
        payload: UpdateMembershipPlanRequest,
        db: Session,
    ) -> MembershipPlanResponse:
        service = MembershipService(db)
        try:
            plan = service.update_plan(plan_id=plan_id, creator_id=current_user.id, payload=payload)
            return MembershipPlanResponse.from_orm_model(plan)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except PermissionError as err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Database integrity constraint violation.",
            )
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def delete_plan(
        plan_id: str,
        current_user: User,
        db: Session,
    ) -> dict:
        service = MembershipService(db)
        try:
            service.delete_plan(plan_id=plan_id, creator_id=current_user.id)
            return {"message": "Membership plan deactivated successfully."}
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except PermissionError as err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))

    @staticmethod
    def subscribe(
        current_user: User,
        payload: SubscribeMembershipRequest,
        db: Session,
    ) -> SubscriptionResponse:
        service = MembershipService(db)
        try:
            sub = service.subscribe(user_id=current_user.id, plan_id=payload.plan_id)
            return SubscriptionResponse.from_orm_model(sub)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except PermissionError as err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have an active subscription to this plan.",
            )
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def get_my_subscriptions(
        current_user: User,
        db: Session,
        status: Optional[SubscriptionStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[SubscriptionResponse]:
        service = MembershipService(db)
        subs = service.get_my_subscriptions(user_id=current_user.id, status=status, skip=skip, limit=limit)
        return [SubscriptionResponse.from_orm_model(s) for s in subs]

    @staticmethod
    def cancel_subscription(
        subscription_id: str,
        current_user: User,
        db: Session,
    ) -> SubscriptionResponse:
        service = MembershipService(db)
        try:
            sub = service.cancel_subscription(subscription_id=subscription_id, user_id=current_user.id)
            return SubscriptionResponse.from_orm_model(sub)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except PermissionError as err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Database integrity constraint violation.",
            )
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
