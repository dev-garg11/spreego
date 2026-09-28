import uuid
from datetime import datetime, timezone
from sqlalchemy import CheckConstraint, Column, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import relationship
from src.config.database import Base


class UserTopicAffinity(Base):
    __tablename__ = "user_topic_affinities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic = Column(String(100), nullable=False, index=True)
    score = Column(Float, nullable=False, default=0.0, server_default="0.0")
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "topic", name="uq_user_topic_affinity"),
        CheckConstraint("score >= 0.0", name="chk_user_topic_affinity_score_non_negative"),
    )

    user = relationship("User", back_populates="topic_affinities")

    def __repr__(self) -> str:
        return f"<UserTopicAffinity(id='{self.id}', user_id='{self.user_id}', topic='{self.topic}', score={self.score})>"
