import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from src.config.database import Base


class ReportEntityType(str, enum.Enum):
    SPREE = "SPREE"
    COMMENT = "COMMENT"
    USER = "USER"
    PRODUCT = "PRODUCT"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            val_upper = value.strip().upper()
            for member in cls:
                if member.value == val_upper:
                    return member
        return None


class ReportReason(str, enum.Enum):
    SPAM = "SPAM"
    HARASSMENT = "HARASSMENT"
    INAPPROPRIATE = "INAPPROPRIATE"
    COPYRIGHT = "COPYRIGHT"
    FRAUD = "FRAUD"
    OTHER = "OTHER"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            val_upper = value.strip().upper()
            for member in cls:
                if member.value == val_upper:
                    return member
        return None


class ReportStatus(str, enum.Enum):
    PENDING = "PENDING"
    REVIEWED = "REVIEWED"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            val_upper = value.strip().upper()
            for member in cls:
                if member.value == val_upper:
                    return member
        return None


class Report(Base):
    __tablename__ = "reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    reporter_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_id = Column(String(255), nullable=False, index=True)
    entity_type = Column(
        SQLEnum(
            ReportEntityType,
            name="report_entity_type_enum",
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    reason = Column(
        SQLEnum(
            ReportReason,
            name="report_reason_enum",
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    description = Column(Text, nullable=True)
    status = Column(
        SQLEnum(
            ReportStatus,
            name="report_status_enum",
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=ReportStatus.PENDING,
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    reporter = relationship("User", foreign_keys=[reporter_id])

    def __repr__(self) -> str:
        return f"<Report(id='{self.id}', reporter='{self.reporter_id}', entity_type='{self.entity_type}', status='{self.status}')>"


class Block(Base):
    __tablename__ = "blocks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    blocker_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    blocked_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        UniqueConstraint("blocker_id", "blocked_id", name="uq_blocker_blocked"),
        CheckConstraint("blocker_id != blocked_id", name="check_block_not_self"),
    )

    blocker = relationship("User", foreign_keys=[blocker_id])
    blocked = relationship("User", foreign_keys=[blocked_id])

    def __repr__(self) -> str:
        return f"<Block(id='{self.id}', blocker='{self.blocker_id}', blocked='{self.blocked_id}')>"


class Mute(Base):
    __tablename__ = "mutes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    muter_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    muted_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        UniqueConstraint("muter_id", "muted_id", name="uq_muter_muted"),
        CheckConstraint("muter_id != muted_id", name="check_mute_not_self"),
    )

    muter = relationship("User", foreign_keys=[muter_id])
    muted = relationship("User", foreign_keys=[muted_id])

    def __repr__(self) -> str:
        return f"<Mute(id='{self.id}', muter='{self.muter_id}', muted='{self.muted_id}')>"
