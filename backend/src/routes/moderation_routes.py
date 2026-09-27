from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.moderation_controller import ModerationController
from src.middlewares.auth_middleware import get_current_user
from src.models.user import User
from src.validations.auth_schemas import MessageResponse
from src.validations.moderation_schemas import (
    BlockedUserItem,
    BlockResponse,
    CreateReportRequest,
    MutedUserItem,
    MuteResponse,
    ReportResponse,
)

router = APIRouter(tags=["Moderation & Safety"])


# ============================================================================
# Reports
# ============================================================================

@router.post(
    "/api/v1/reports",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Report abusive content or user",
)
@router.post(
    "/api/v1/reports/",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
@router.post(
    "/api/v1/moderation/reports",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
@router.post(
    "/api/v1/moderation/reports/",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_report(
    payload: CreateReportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportResponse:
    return ModerationController.create_report(
        current_user=current_user,
        payload=payload,
        db=db,
    )


# ============================================================================
# Blocks
# ============================================================================

@router.post(
    "/api/v1/users/{id}/block",
    response_model=BlockResponse,
    status_code=status.HTTP_200_OK,
    summary="Block a user",
)
@router.post(
    "/api/v1/users/{id}/block/",
    response_model=BlockResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.post(
    "/api/v1/moderation/users/{id}/block",
    response_model=BlockResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.post(
    "/api/v1/moderation/users/{id}/block/",
    response_model=BlockResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def block_user(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BlockResponse:
    return ModerationController.block_user(
        target_user_id=id,
        current_user=current_user,
        db=db,
    )


@router.delete(
    "/api/v1/users/{id}/block",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Unblock a user",
)
@router.delete(
    "/api/v1/users/{id}/block/",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.delete(
    "/api/v1/moderation/users/{id}/block",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.delete(
    "/api/v1/moderation/users/{id}/block/",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def unblock_user(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    return ModerationController.unblock_user(
        target_user_id=id,
        current_user=current_user,
        db=db,
    )


@router.get(
    "/api/v1/users/me/blocked",
    response_model=List[BlockedUserItem],
    status_code=status.HTTP_200_OK,
    summary="List blocked users for current user",
)
@router.get(
    "/api/v1/users/me/blocked/",
    response_model=List[BlockedUserItem],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.get(
    "/api/v1/moderation/blocked",
    response_model=List[BlockedUserItem],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.get(
    "/api/v1/moderation/blocked/",
    response_model=List[BlockedUserItem],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.get(
    "/api/v1/moderation/users/me/blocked",
    response_model=List[BlockedUserItem],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.get(
    "/api/v1/moderation/users/me/blocked/",
    response_model=List[BlockedUserItem],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_blocked_users(
    page: Optional[int] = Query(None, ge=1, description="Page number (1-indexed)"),
    skip: Optional[int] = Query(None, ge=0, description="Offset"),
    limit: int = Query(50, ge=1, le=100, description="Page size limit"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[BlockedUserItem]:
    offset = (page - 1) * limit if page is not None else (skip or 0)
    return ModerationController.get_blocked_users(
        current_user=current_user,
        skip=offset,
        limit=limit,
        db=db,
    )


# ============================================================================
# Mutes
# ============================================================================

@router.post(
    "/api/v1/users/{id}/mute",
    response_model=MuteResponse,
    status_code=status.HTTP_200_OK,
    summary="Mute a user",
)
@router.post(
    "/api/v1/users/{id}/mute/",
    response_model=MuteResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.post(
    "/api/v1/moderation/users/{id}/mute",
    response_model=MuteResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.post(
    "/api/v1/moderation/users/{id}/mute/",
    response_model=MuteResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def mute_user(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MuteResponse:
    return ModerationController.mute_user(
        target_user_id=id,
        current_user=current_user,
        db=db,
    )


@router.delete(
    "/api/v1/users/{id}/mute",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Unmute a user",
)
@router.delete(
    "/api/v1/users/{id}/mute/",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.delete(
    "/api/v1/moderation/users/{id}/mute",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.delete(
    "/api/v1/moderation/users/{id}/mute/",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def unmute_user(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    return ModerationController.unmute_user(
        target_user_id=id,
        current_user=current_user,
        db=db,
    )


@router.get(
    "/api/v1/users/me/muted",
    response_model=List[MutedUserItem],
    status_code=status.HTTP_200_OK,
    summary="List muted users for current user",
)
@router.get(
    "/api/v1/users/me/muted/",
    response_model=List[MutedUserItem],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.get(
    "/api/v1/moderation/muted",
    response_model=List[MutedUserItem],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.get(
    "/api/v1/moderation/muted/",
    response_model=List[MutedUserItem],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.get(
    "/api/v1/moderation/users/me/muted",
    response_model=List[MutedUserItem],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.get(
    "/api/v1/moderation/users/me/muted/",
    response_model=List[MutedUserItem],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_muted_users(
    page: Optional[int] = Query(None, ge=1, description="Page number (1-indexed)"),
    skip: Optional[int] = Query(None, ge=0, description="Offset"),
    limit: int = Query(50, ge=1, le=100, description="Page size limit"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[MutedUserItem]:
    offset = (page - 1) * limit if page is not None else (skip or 0)
    return ModerationController.get_muted_users(
        current_user=current_user,
        skip=offset,
        limit=limit,
        db=db,
    )
