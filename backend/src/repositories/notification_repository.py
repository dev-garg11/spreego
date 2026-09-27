from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from src.models.notification import Notification, NotificationType
from src.repositories.base_repository import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, db: Session):
        super().__init__(Notification, db)

    def get_user_notifications(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        unread_only: Optional[bool] = None,
        notification_type: Optional[NotificationType] = None,
    ) -> List[Notification]:
        query = self.db.query(Notification).filter(Notification.recipient_id == user_id)
        if unread_only is True:
            query = query.filter(Notification.is_read.is_(False))
        elif unread_only is False:
            query = query.filter(Notification.is_read.is_(True))
        if notification_type is not None:
            query = query.filter(Notification.type == notification_type)
        return (
            query.order_by(Notification.created_at.desc(), Notification.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_unread(self, user_id: str) -> int:
        return (
            self.db.query(func.count(Notification.id))
            .filter(Notification.recipient_id == user_id, Notification.is_read.is_(False))
            .scalar()
            or 0
        )

    def mark_all_as_read(self, user_id: str) -> int:
        try:
            updated = (
                self.db.query(Notification)
                .filter(Notification.recipient_id == user_id, Notification.is_read.is_(False))
                .update({Notification.is_read: True}, synchronize_session="fetch")
            )
            self.db.commit()
            return updated
        except Exception:
            self.db.rollback()
            raise
