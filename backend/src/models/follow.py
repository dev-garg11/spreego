import uuid
from datetime import datetime, timezone
from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import relationship
from src.config.database import Base


class Follow(Base):
    __tablename__ = "follows"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    follower_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    following_id = Column(
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
        UniqueConstraint("follower_id", "following_id", name="uq_follower_following"),
        CheckConstraint("follower_id != following_id", name="ck_prevent_self_follow"),
    )

    # Relationships
    follower = relationship("User", foreign_keys=[follower_id], back_populates="following")
    following = relationship("User", foreign_keys=[following_id], back_populates="followers")

    def __repr__(self) -> str:
        return f"<Follow(follower_id='{self.follower_id}', following_id='{self.following_id}')>"
