import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from src.config.database import Base


class NotificationType(str, enum.Enum):
    CLAP = "CLAP"
    COMMENT = "COMMENT"
    FOLLOW = "FOLLOW"
    ORDER_PLACED = "ORDER_PLACED"
    ORDER_STATUS = "ORDER_STATUS"
    PAYOUT = "PAYOUT"
    OPEN_SUBMISSION = "OPEN_SUBMISSION"
    SYSTEM = "SYSTEM"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            val_upper = value.strip().upper()
            for member in cls:
                if member.value == val_upper:
                    return member
        return None


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    recipient_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    type = Column(
        SQLEnum(
            NotificationType,
            name="notification_type_enum",
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    entity_id = Column(String(255), nullable=True)
    entity_type = Column(String(64), nullable=True)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationships
    recipient = relationship("User", foreign_keys=[recipient_id])
    actor = relationship("User", foreign_keys=[actor_id])

    def __repr__(self) -> str:
        return f"<Notification(id='{self.id}', recipient='{self.recipient_id}', type='{self.type}', is_read={self.is_read})>"
