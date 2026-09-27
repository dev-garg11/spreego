from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.notification_controller import NotificationController
from src.middlewares.auth_middleware import get_current_user
from src.models.notification import NotificationType
from src.models.user import User
from src.validations.notification_schemas import (
    NotificationResponse,
    ReadAllResponse,
    UnreadCountResponse,
)

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=List[NotificationResponse],
    status_code=status.HTTP_200_OK,
    summary="Get paginated notifications for current user",
)
@router.get(
    "/",
    response_model=List[NotificationResponse],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_notifications(
    page: Optional[int] = Query(None, ge=1, description="Page number (1-indexed)"),
    skip: Optional[int] = Query(None, ge=0, description="Offset"),
    limit: int = Query(20, ge=1, le=100, description="Page size limit"),
    unread_only: Optional[bool] = Query(None, description="Filter for unread notifications only"),
    type: Optional[NotificationType] = Query(None, description="Filter by notification type"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[NotificationResponse]:
    offset = (page - 1) * limit if page is not None else (skip or 0)
    return NotificationController.get_notifications(
        current_user=current_user,
        skip=offset,
        limit=limit,
        unread_only=unread_only,
        notification_type=type,
        db=db,
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    status_code=status.HTTP_200_OK,
    summary="Get unread notification count badge",
)
@router.get(
    "/unread-count/",
    response_model=UnreadCountResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UnreadCountResponse:
    return NotificationController.get_unread_count(current_user=current_user, db=db)


@router.patch(
    "/{id}/read",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark single notification as read",
)
@router.patch(
    "/{id}/read/",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def mark_as_read(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationResponse:
    return NotificationController.mark_as_read(
        notification_id=id,
        current_user=current_user,
        db=db,
    )


@router.post(
    "/read-all",
    response_model=ReadAllResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark all notifications as read",
)
@router.post(
    "/read-all/",
    response_model=ReadAllResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def mark_all_as_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReadAllResponse:
    return NotificationController.mark_all_as_read(current_user=current_user, db=db)
