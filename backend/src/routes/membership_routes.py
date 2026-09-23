from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.membership_controller import MembershipController
from src.middlewares.auth_middleware import get_current_user, get_optional_current_user
from src.models.membership import SubscriptionStatus
from src.models.user import User
from src.validations.membership_schemas import (
    CreateMembershipPlanRequest,
    MembershipPlanResponse,
    SubscribeMembershipRequest,
    SubscriptionResponse,
    UpdateMembershipPlanRequest,
)

router = APIRouter(prefix="/api/v1/memberships", tags=["Memberships"])


# ============================================================================
# 1. Query Plans (GET /api/v1/memberships/plans)
# ============================================================================

@router.get(
    "/plans",
    response_model=List[MembershipPlanResponse],
    status_code=status.HTTP_200_OK,
    summary="Query available plans for a creator (filters out unauthorized VIP tiers)",
)
@router.get(
    "/plans/",
    response_model=List[MembershipPlanResponse],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def list_plans(
    creator_id: Optional[str] = Query(None, description="Query plans for a specific creator"),
    skip: int = Query(0, ge=0, description="Offset"),
    limit: int = Query(50, ge=1, le=100, description="Limit"),
    db: Session = Depends(get_db),
) -> List[MembershipPlanResponse]:
    """Query available active plans for a creator. Returns ₹0 Free plans when VIP mode is disabled."""
    return MembershipController.list_plans(
        creator_id=creator_id,
        skip=skip,
        limit=limit,
        db=db,
    )


# ============================================================================
# 2. Create Plan (POST /api/v1/memberships/plans)
# ============================================================================

@router.post(
    "/plans",
    response_model=MembershipPlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a membership plan (creator ID strictly derived from JWT)",
)
@router.post(
    "/plans/",
    response_model=MembershipPlanResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_plan(
    payload: CreateMembershipPlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MembershipPlanResponse:
    """Authenticated creator endpoint to create a membership plan. Validates price constraints."""
    return MembershipController.create_plan(
        current_user=current_user,
        payload=payload,
        db=db,
    )


# ============================================================================
# 3. Get Plan by ID (GET /api/v1/memberships/plans/{id})
# ============================================================================

@router.get(
    "/plans/{id}",
    response_model=MembershipPlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single membership plan details",
)
@router.get(
    "/plans/{id}/",
    response_model=MembershipPlanResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_plan(
    id: str,
    requesting_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> MembershipPlanResponse:
    """View details of a single membership plan."""
    return MembershipController.get_plan(
        plan_id=id,
        requesting_user=requesting_user,
        db=db,
    )


# ============================================================================
# 4. Update Plan (PATCH /api/v1/memberships/plans/{id})
# ============================================================================

@router.patch(
    "/plans/{id}",
    response_model=MembershipPlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a membership plan (creator only)",
)
@router.patch(
    "/plans/{id}/",
    response_model=MembershipPlanResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def update_plan(
    id: str,
    payload: UpdateMembershipPlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MembershipPlanResponse:
    """Authenticated creator endpoint to update their own membership plan."""
    return MembershipController.update_plan(
        plan_id=id,
        current_user=current_user,
        payload=payload,
        db=db,
    )


# ============================================================================
# 5. Delete / Deactivate Plan (DELETE /api/v1/memberships/plans/{id})
# ============================================================================

@router.delete(
    "/plans/{id}",
    status_code=status.HTTP_200_OK,
    summary="Deactivate a membership plan (creator only)",
)
@router.delete(
    "/plans/{id}/",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def delete_plan(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Authenticated creator endpoint to deactivate their membership plan."""
    return MembershipController.delete_plan(
        plan_id=id,
        current_user=current_user,
        db=db,
    )


# ============================================================================
# 6. Subscribe (POST /api/v1/memberships/subscribe)
# ============================================================================

@router.post(
    "/subscribe",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subscribe to a creator membership plan (instant ₹0 activation)",
)
@router.post(
    "/subscribe/",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def subscribe(
    payload: SubscribeMembershipRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubscriptionResponse:
    """Authenticated user endpoint to subscribe. For ₹0 plans, instantly provisions ACTIVE status."""
    return MembershipController.subscribe(
        current_user=current_user,
        payload=payload,
        db=db,
    )


# ============================================================================
# 7. Get My Subscriptions (GET /api/v1/memberships/my)
# ============================================================================

@router.get(
    "/my",
    response_model=List[SubscriptionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get all active and past memberships of the current user",
)
@router.get(
    "/my/",
    response_model=List[SubscriptionResponse],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_my_subscriptions(
    status: Optional[SubscriptionStatus] = Query(None, description="Filter memberships by status (ACTIVE, CANCELLED, EXPIRED)"),
    skip: int = Query(0, ge=0, description="Offset"),
    limit: int = Query(100, ge=1, le=100, description="Limit"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[SubscriptionResponse]:
    """Authenticated endpoint returning all active and past memberships of requesting user."""
    return MembershipController.get_my_subscriptions(
        current_user=current_user,
        db=db,
        status=status,
        skip=skip,
        limit=limit,
    )


# ============================================================================
# 8. Cancel Subscription (POST /api/v1/memberships/{id}/cancel)
# ============================================================================

@router.post(
    "/{id}/cancel",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel a subscription",
)
@router.post(
    "/{id}/cancel/",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.post(
    "/subscriptions/{id}/cancel",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.post(
    "/subscriptions/{id}/cancel/",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.post(
    "/plans/{id}/cancel",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.post(
    "/plans/{id}/cancel/",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def cancel_subscription(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubscriptionResponse:
    """Authenticated endpoint to cancel a subscription."""
    return MembershipController.cancel_subscription(
        subscription_id=id,
        current_user=current_user,
        db=db,
    )
