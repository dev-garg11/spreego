from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from src.models.notification import NotificationType
from src.models.user import User
from src.services.notification_service import NotificationService
from src.validations.notification_schemas import (
    NotificationResponse,
    ReadAllResponse,
    UnreadCountResponse,
)


class NotificationController:
    @staticmethod
    def get_notifications(
        current_user: User,
        skip: int,
        limit: int,
        unread_only: Optional[bool],
        notification_type: Optional[NotificationType],
        db: Session,
    ) -> List[NotificationResponse]:
        service = NotificationService(db)
        notifs = service.get_notifications(
            current_user=current_user,
            skip=skip,
            limit=limit,
            unread_only=unread_only,
            notification_type=notification_type,
        )
        return [NotificationResponse.model_validate(n) for n in notifs]

    @staticmethod
    def get_unread_count(current_user: User, db: Session) -> UnreadCountResponse:
        service = NotificationService(db)
        return service.get_unread_count(current_user=current_user)

    @staticmethod
    def mark_as_read(notification_id: str, current_user: User, db: Session) -> NotificationResponse:
        service = NotificationService(db)
        try:
            notif = service.mark_as_read(notification_id=notification_id, current_user=current_user)
            return NotificationResponse.model_validate(notif)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except PermissionError as err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def mark_all_as_read(current_user: User, db: Session) -> ReadAllResponse:
        service = NotificationService(db)
        return service.mark_all_as_read(current_user=current_user)
