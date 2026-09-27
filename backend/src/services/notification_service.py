from typing import List, Optional, Union
from sqlalchemy.orm import Session
from src.models.notification import Notification, NotificationType
from src.models.user import User
from src.repositories.notification_repository import NotificationRepository
from src.validations.notification_schemas import (
    NotificationResponse,
    ReadAllResponse,
    UnreadCountResponse,
)


class NotificationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = NotificationRepository(db)

    def create_notification(
        self_or_db=None,
        *args,
        **kwargs,
    ) -> Notification:
        """
        Dispatches a notification.
        Supports both instance and class calls:
        - service.create_notification(recipient_id=..., type=..., title=..., message=..., ...)
        - NotificationService.create_notification(db, recipient_id=..., type=..., title=..., message=..., ...)
        - NotificationService.create_notification(db=db, recipient_id=..., ...)
        - NotificationService.create_notification("user-id", NotificationType.CLAP, "Title", "Msg", db=db)
        """
        if isinstance(self_or_db, NotificationService):
            repo = self_or_db.repo
        elif isinstance(self_or_db, Session):
            repo = NotificationRepository(self_or_db)
        elif "db" in kwargs:
            db = kwargs.pop("db")
            repo = NotificationRepository(db)
            if self_or_db is not None:
                args = (self_or_db,) + args
        else:
            raise ValueError("A database Session is required to create a notification.")

        recipient_id = kwargs.get("recipient_id") or (args[0] if len(args) > 0 else None)
        notif_type = kwargs.get("type") or kwargs.get("notification_type") or (args[1] if len(args) > 1 else None)
        title = kwargs.get("title") or (args[2] if len(args) > 2 else None)
        message = kwargs.get("message") or (args[3] if len(args) > 3 else None)
        actor_id = kwargs.get("actor_id") or (args[4] if len(args) > 4 else None)
        entity_id = kwargs.get("entity_id") or (args[5] if len(args) > 5 else None)
        entity_type = kwargs.get("entity_type") or (args[6] if len(args) > 6 else None)

        clean_recipient_id = recipient_id.strip() if isinstance(recipient_id, str) else recipient_id
        if not clean_recipient_id:
            raise ValueError("recipient_id is required.")
        if not notif_type:
            raise ValueError("type is required.")
        clean_title = title.strip() if isinstance(title, str) else title
        if not clean_title:
            raise ValueError("title is required.")
        clean_message = message.strip() if isinstance(message, str) else message
        if not clean_message:
            raise ValueError("message is required.")

        if isinstance(notif_type, str):
            notif_type = NotificationType(notif_type.strip().upper())

        clean_actor_id = actor_id.strip() if isinstance(actor_id, str) and actor_id.strip() else None
        clean_entity_id = entity_id.strip() if isinstance(entity_id, str) and entity_id.strip() else None
        clean_entity_type = entity_type.strip() if isinstance(entity_type, str) and entity_type.strip() else None

        notif = Notification(
            recipient_id=clean_recipient_id,
            actor_id=clean_actor_id,
            type=notif_type,
            title=clean_title,
            message=clean_message,
            entity_id=clean_entity_id,
            entity_type=clean_entity_type,
            is_read=False,
        )
        return repo.create(notif)

    @classmethod
    def dispatch(cls, db: Session, **kwargs) -> Notification:
        """Alias helper to dispatch notifications on events."""
        return cls.create_notification(db=db, **kwargs)

    def get_notifications(
        self,
        current_user: User,
        skip: int = 0,
        limit: int = 20,
        unread_only: Optional[bool] = None,
        notification_type: Optional[NotificationType] = None,
    ) -> List[Notification]:
        return self.repo.get_user_notifications(
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            unread_only=unread_only,
            notification_type=notification_type,
        )

    def get_unread_count(self, current_user: User) -> UnreadCountResponse:
        count = self.repo.count_unread(current_user.id)
        return UnreadCountResponse(unread_count=count)

    def mark_as_read(self, notification_id: str, current_user: User) -> Notification:
        clean_id = notification_id.strip() if notification_id else ""
        if not clean_id:
            raise LookupError("Notification not found.")
        notif = self.repo.get_by_id(clean_id)
        if not notif:
            raise LookupError("Notification not found.")
        if notif.recipient_id != current_user.id:
            raise PermissionError("You do not have access to this notification.")
        if not notif.is_read:
            notif.is_read = True
            self.repo.update(notif)
        return notif

    def mark_all_as_read(self, current_user: User) -> ReadAllResponse:
        updated = self.repo.mark_all_as_read(current_user.id)
        return ReadAllResponse(message="All notifications marked as read.", updated_count=updated)
