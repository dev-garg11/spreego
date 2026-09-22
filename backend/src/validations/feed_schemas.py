from datetime import datetime
from typing import Optional
from pydantic import Field
from src.models.spree import SpreeType, SpreeVisibility
from src.validations.auth_schemas import BaseSchema


class FeedCreatorInfo(BaseSchema):
    id: str
    username: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


class FeedEngagementMetrics(BaseSchema):
    views_count: int = 0
    completed_views_count: int = 0
    watch_completion_rate: float = 0.0
    claps_count: int = 0
    comments_count: int = 0
    saves_count: int = 0
    shares_count: int = 0


class FeedSpreeResponse(BaseSchema):
    id: str
    creator_id: str
    type: SpreeType
    title: str
    description: Optional[str] = None
    media_url: str
    thumbnail_url: Optional[str] = None
    duration: Optional[float] = None
    visibility: SpreeVisibility
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    creator: Optional[FeedCreatorInfo] = None
    metrics: FeedEngagementMetrics = Field(default_factory=FeedEngagementMetrics)
    views_count: int = 0
    claps_count: int = 0
    comments_count: int = 0
    saves_count: int = 0
    shares_count: int = 0
    score: Optional[float] = None
    is_buzzer_active: bool = False
    boost_multiplier: float = 1.0
