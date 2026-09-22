import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Enum as SAEnum, Float, ForeignKey, Index, String
from sqlalchemy.orm import relationship
from src.config.database import Base


class BuzzerStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class BuzzerCampaign(Base):
    __tablename__ = "buzzer_campaigns"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    spree_id = Column(
        String(36),
        ForeignKey("sprees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    creator_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
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
        SAEnum(BuzzerStatus, name="buzzer_status", native_enum=False, values_callable=lambda obj: [e.value for e in obj]),
        default=BuzzerStatus.ACTIVE,
        server_default=BuzzerStatus.ACTIVE.value,
        nullable=False,
        index=True,
    )
    boost_multiplier = Column(
        Float,
        default=1.5,
        server_default="1.5",
        nullable=False,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "uq_buzzer_campaign_active_spree",
            "spree_id",
            unique=True,
            postgresql_where=(status == "ACTIVE"),
            sqlite_where=(status == "ACTIVE"),
        ),
    )

    # Relationships
    spree = relationship("Spree", back_populates="buzzer_campaigns")
    creator = relationship("User", back_populates="buzzer_campaigns")

    @property
    def is_active(self) -> bool:
        if self.status != BuzzerStatus.ACTIVE:
            return False
        if not self.start_at or not self.end_at:
            return False
        now = datetime.now(timezone.utc)
        start = self.start_at
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        end = self.end_at
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        return start <= now <= end

    def __repr__(self) -> str:
        return f"<BuzzerCampaign(id='{self.id}', spree_id='{self.spree_id}', status='{self.status}', multiplier={self.boost_multiplier})>"
