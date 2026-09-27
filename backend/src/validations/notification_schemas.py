from datetime import datetime
from typing import Optional
from pydantic import Field
from src.models.notification import NotificationType
from src.validations.auth_schemas import BaseSchema


class CreateNotificationRequest(BaseSchema):
    recipient_id: str
    type: NotificationType
    title: str = Field(..., max_length=255)
    message: str
    actor_id: Optional[str] = None
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None


class NotificationResponse(BaseSchema):
    id: str
    recipient_id: str
    actor_id: Optional[str] = None
    type: NotificationType
    title: str
    message: str
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    is_read: bool
    created_at: datetime


class UnreadCountResponse(BaseSchema):
    unread_count: int


class ReadAllResponse(BaseSchema):
    message: str = "All notifications marked as read."
    updated_count: int = 0
