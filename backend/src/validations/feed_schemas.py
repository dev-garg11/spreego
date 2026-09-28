from datetime import datetime
from typing import Optional
from pydantic import Field, field_validator
from src.models.spree import SpreeType, SpreeVisibility
from src.validations.auth_schemas import BaseSchema
from src.validations.spree_schemas import _clean_tags_list


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
    category: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
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

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, v):
        return _clean_tags_list(v)

