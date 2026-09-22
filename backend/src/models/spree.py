import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Enum as SAEnum, Float, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from src.config.database import Base


class SpreeType(str, enum.Enum):
    VIDEO_SHORT = "VIDEO_SHORT"
    VIDEO_LONG = "VIDEO_LONG"
    PHOTO = "PHOTO"
    SERIES = "SERIES"


class SpreeVisibility(str, enum.Enum):
    PUBLIC = "PUBLIC"
    FOLLOWERS_ONLY = "FOLLOWERS_ONLY"
    PRIVATE = "PRIVATE"


class Spree(Base):
    __tablename__ = "sprees"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    creator_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type = Column(
        SAEnum(SpreeType, name="spree_type", native_enum=False, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    media_url = Column(String(1024), nullable=False)
    thumbnail_url = Column(String(1024), nullable=True)
    duration = Column(Float, nullable=True)
    visibility = Column(
        SAEnum(SpreeVisibility, name="spree_visibility", native_enum=False, values_callable=lambda obj: [e.value for e in obj]),
        default=SpreeVisibility.PUBLIC,
        server_default=SpreeVisibility.PUBLIC.value,
        nullable=False,
        index=True,
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
    creator = relationship("User", back_populates="sprees")
    views = relationship("SpreeView", back_populates="spree", cascade="all, delete-orphan", lazy="select")
    claps = relationship("SpreeClap", back_populates="spree", cascade="all, delete-orphan", lazy="select")
    comments = relationship("SpreeComment", back_populates="spree", cascade="all, delete-orphan", lazy="select")
    saves = relationship("SpreeSave", back_populates="spree", cascade="all, delete-orphan", lazy="select")
    shares = relationship("SpreeShare", back_populates="spree", cascade="all, delete-orphan", lazy="select")
    buzzer_campaigns = relationship("BuzzerCampaign", back_populates="spree", cascade="all, delete-orphan", lazy="select")

    @property
    def active_buzzer_campaign(self):
        for campaign in self.buzzer_campaigns:
            if campaign.is_active:
                return campaign
        return None

    def __repr__(self) -> str:
        return f"<Spree(id='{self.id}', type='{self.type}', title='{self.title}', creator_id='{self.creator_id}')>"
