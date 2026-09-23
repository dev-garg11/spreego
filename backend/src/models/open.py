import enum
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional
from sqlalchemy import (
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import backref, relationship
from src.config.database import Base


class OpenType(str, enum.Enum):
    CHALLENGE = "CHALLENGE"
    COMPETITION = "COMPETITION"
    SPONSORED = "SPONSORED"


class OpenStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


DEFAULT_SCORING_CONFIG: Dict[str, float] = {
    "claps": 2.0,
    "views": 1.0,
    "shares": 3.0,
    "completion": 5.0,
}


class Open(Base):
    __tablename__ = "opens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    creator_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type = Column(
        SAEnum(OpenType, name="open_type", native_enum=False, values_callable=lambda obj: [e.value for e in obj]),
        default=OpenType.CHALLENGE,
        server_default=OpenType.CHALLENGE.value,
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    cover_image_url = Column(String(1024), nullable=True)
    rules = Column(Text, nullable=True)
    start_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    end_at = Column(
        DateTime(timezone=True),
        nullable=False,
    )
    status = Column(
        SAEnum(OpenStatus, name="open_status", native_enum=False, values_callable=lambda obj: [e.value for e in obj]),
        default=OpenStatus.ACTIVE,
        server_default=OpenStatus.ACTIVE.value,
        nullable=False,
        index=True,
    )
    reward_info = Column(Text, nullable=True)
    max_participants = Column(Integer, nullable=True)
    scoring_config = Column(
        JSON,
        nullable=False,
        default=lambda: dict(DEFAULT_SCORING_CONFIG),
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    creator = relationship("User", backref=backref("created_opens", cascade="all, delete-orphan", passive_deletes=True))
    participants = relationship("OpenParticipant", back_populates="open", cascade="all, delete-orphan", lazy="select", passive_deletes=True)
    submissions = relationship("OpenSubmission", back_populates="open", cascade="all, delete-orphan", lazy="select", passive_deletes=True)

    @property
    def is_active(self) -> bool:
        if self.status != OpenStatus.ACTIVE:
            return False
        if not self.start_at or not self.end_at:
            return False
        now = datetime.now(timezone.utc)
        start = self.start_at
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        else:
            start = start.astimezone(timezone.utc)
        end = self.end_at
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        else:
            end = end.astimezone(timezone.utc)
        return start <= now <= end

    # ponytail: relationship length count via selectinload; switch to column_property(count) if participant lists exceed 50k
    @property
    def participants_count(self) -> int:
        if self.participants is not None:
            return len(self.participants)
        return 0

    @property
    def submissions_count(self) -> int:
        if self.submissions is not None:
            return len(self.submissions)
        return 0

    def __repr__(self) -> str:
        return f"<Open(id='{self.id}', type='{self.type}', title='{self.title}', status='{self.status}')>"


class OpenParticipant(Base):
    __tablename__ = "open_participants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    open_id = Column(
        String(36),
        ForeignKey("opens.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    joined_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("open_id", "user_id", name="uq_open_participants_open_user"),
    )

    # Relationships
    open = relationship("Open", back_populates="participants")
    user = relationship("User", backref=backref("open_participations", cascade="all, delete-orphan", passive_deletes=True))

    def __repr__(self) -> str:
        return f"<OpenParticipant(id='{self.id}', open_id='{self.open_id}', user_id='{self.user_id}')>"


class OpenSubmission(Base):
    __tablename__ = "open_submissions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    open_id = Column(
        String(36),
        ForeignKey("opens.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    spree_id = Column(
        String(36),
        ForeignKey("sprees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score = Column(Float, default=0.0, server_default="0.0", nullable=False)
    rank = Column(Integer, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("open_id", "spree_id", name="uq_open_submissions_open_spree"),
    )

    # Relationships
    open = relationship("Open", back_populates="submissions")
    user = relationship("User", backref=backref("open_submissions", cascade="all, delete-orphan", passive_deletes=True))
    spree = relationship("Spree", backref=backref("open_submissions", cascade="all, delete-orphan", passive_deletes=True))

    def __repr__(self) -> str:
        return f"<OpenSubmission(id='{self.id}', open_id='{self.open_id}', spree_id='{self.spree_id}', score={self.score}, rank={self.rank})>"
