import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import backref, relationship
from src.config.database import Base


class MembershipTierType(str, enum.Enum):
    FREE = "FREE"
    VIP = "VIP"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class MembershipPlan(Base):
    __tablename__ = "membership_plans"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    creator_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    monthly_price = Column(Float, default=0.0, server_default="0.0", nullable=False)
    currency = Column(String(10), default="INR", server_default="INR", nullable=False)
    tier_type = Column(
        SAEnum(
            MembershipTierType,
            name="membership_tier_type",
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=MembershipTierType.FREE,
        server_default=MembershipTierType.FREE.value,
        nullable=False,
        index=True,
    )
    benefits = Column(JSON, nullable=False, default=list, server_default="'[]'")
    is_active = Column(Boolean, default=True, server_default="1", nullable=False, index=True)
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
    creator = relationship(
        "User",
        backref=backref("membership_plans", cascade="all, delete-orphan", passive_deletes=True),
    )
    subscriptions = relationship(
        "Subscription",
        back_populates="plan",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # ponytail: in-memory active count; switch to SQL count subquery when per-plan subscriber count exceeds 50k
    @property
    def subscribers_count(self) -> int:
        if self.subscriptions is not None:
            return sum(1 for s in self.subscriptions if s.status == SubscriptionStatus.ACTIVE)
        return 0

    @property
    def is_free(self) -> bool:
        return self.monthly_price == 0.0 and self.tier_type == MembershipTierType.FREE

    def __repr__(self) -> str:
        return f"<MembershipPlan(id='{self.id}', name='{self.name}', tier_type='{self.tier_type}', monthly_price={self.monthly_price})>"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    plan_id = Column(
        String(36),
        ForeignKey("membership_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(
        SAEnum(
            SubscriptionStatus,
            name="subscription_status",
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=SubscriptionStatus.ACTIVE,
        server_default=SubscriptionStatus.ACTIVE.value,
        nullable=False,
        index=True,
    )
    current_period_start = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    current_period_end = Column(
        DateTime(timezone=True),
        nullable=False,
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

    __table_args__ = (
        Index(
            "uq_active_plan_user",
            "plan_id",
            "user_id",
            unique=True,
            postgresql_where=(status == "ACTIVE"),
            sqlite_where=(status == "ACTIVE"),
        ),
    )

    # Relationships
    plan = relationship("MembershipPlan", back_populates="subscriptions")
    user = relationship(
        "User",
        backref=backref("subscriptions", cascade="all, delete-orphan", passive_deletes=True),
    )

    def __repr__(self) -> str:
        return f"<Subscription(id='{self.id}', plan_id='{self.plan_id}', user_id='{self.user_id}', status='{self.status}')>"
