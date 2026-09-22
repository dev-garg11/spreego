import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import backref, relationship
from src.config.database import Base


class SpreeView(Base):
    __tablename__ = "spree_views"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    spree_id = Column(
        String(36),
        ForeignKey("sprees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    watch_duration = Column(Float, nullable=False, default=0.0)
    completed = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    spree = relationship("Spree", back_populates="views")
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<SpreeView(id='{self.id}', spree_id='{self.spree_id}', user_id='{self.user_id}', duration={self.watch_duration})>"


class SpreeClap(Base):
    __tablename__ = "spree_claps"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    spree_id = Column(
        String(36),
        ForeignKey("sprees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("spree_id", "user_id", name="uq_spree_claps_spree_user"),
    )

    # Relationships
    spree = relationship("Spree", back_populates="claps")
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<SpreeClap(id='{self.id}', spree_id='{self.spree_id}', user_id='{self.user_id}')>"


class SpreeComment(Base):
    __tablename__ = "spree_comments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    spree_id = Column(
        String(36),
        ForeignKey("sprees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    text = Column(Text, nullable=False)
    parent_id = Column(
        String(36),
        ForeignKey("spree_comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    spree = relationship("Spree", back_populates="comments")
    user = relationship("User", lazy="joined")
    parent = relationship("SpreeComment", remote_side=[id], backref=backref("replies", cascade="all, delete-orphan"))

    def __repr__(self) -> str:
        return f"<SpreeComment(id='{self.id}', spree_id='{self.spree_id}', user_id='{self.user_id}')>"


class SpreeSave(Base):
    __tablename__ = "spree_saves"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    spree_id = Column(
        String(36),
        ForeignKey("sprees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("spree_id", "user_id", name="uq_spree_saves_spree_user"),
    )

    # Relationships
    spree = relationship("Spree", back_populates="saves")
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<SpreeSave(id='{self.id}', spree_id='{self.spree_id}', user_id='{self.user_id}')>"


class SpreeShare(Base):
    __tablename__ = "spree_shares"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    spree_id = Column(
        String(36),
        ForeignKey("sprees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    platform = Column(String(64), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    spree = relationship("Spree", back_populates="shares")
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<SpreeShare(id='{self.id}', spree_id='{self.spree_id}', platform='{self.platform}')>"
