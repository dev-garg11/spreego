from datetime import datetime
from typing import Dict, Optional
from pydantic import Field, field_validator
from src.models.open import DEFAULT_SCORING_CONFIG, OpenStatus, OpenType
from src.validations.auth_schemas import BaseSchema
from src.validations.feed_schemas import FeedCreatorInfo, FeedEngagementMetrics, FeedSpreeResponse


class CreateOpenRequest(BaseSchema):
    type: OpenType = Field(default=OpenType.CHALLENGE, description="Open type: CHALLENGE, COMPETITION, SPONSORED")
    title: str = Field(..., max_length=255, description="Open title")
    description: Optional[str] = Field(None, max_length=10000, description="Detailed description")
    cover_image_url: Optional[str] = Field(None, max_length=1024, description="Optional cover image URL")
    rules: Optional[str] = Field(None, max_length=10000, description="Optional rules or instructions")
    start_at: Optional[datetime] = Field(None, description="Start datetime (defaults to now)")
    end_at: datetime = Field(..., description="End datetime (must be after start_at)")
    status: Optional[OpenStatus] = Field(default=OpenStatus.ACTIVE, description="Open status")
    reward_info: Optional[str] = Field(None, max_length=1000, description="Optional rewards/prize details")
    max_participants: Optional[int] = Field(None, ge=1, description="Optional maximum allowed participants")
    scoring_config: Optional[Dict[str, float]] = Field(None, description="Dynamic ranking metric weights")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Title cannot be empty.")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v

    @field_validator("cover_image_url")
    @classmethod
    def validate_cover_image_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v

    @field_validator("rules")
    @classmethod
    def validate_rules(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v

    @field_validator("reward_info")
    @classmethod
    def validate_reward_info(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v

    @field_validator("scoring_config")
    @classmethod
    def validate_scoring_config(cls, v: Optional[Dict[str, float]]) -> Optional[Dict[str, float]]:
        if v is not None:
            if not v:
                raise ValueError("scoring_config cannot be an empty dictionary.")
            import math
            cleaned: Dict[str, float] = {}
            for k, val in v.items():
                if not isinstance(k, str) or not k.strip():
                    raise ValueError("Scoring metric name cannot be empty.")
                clean_k = k.strip().lower()
                if clean_k.startswith("_") or not clean_k.isidentifier():
                    raise ValueError(f"Invalid metric name: '{k}'. Metric names must be valid identifiers without leading underscores.")
                if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
                    raise ValueError(f"Weight for '{k}' must be a finite number.")
                if val < 0:
                    raise ValueError(f"Weight for '{k}' cannot be negative.")
                cleaned[clean_k] = float(val)
            return cleaned
        return v


class OpenResponse(BaseSchema):
    id: str
    creator_id: str
    type: OpenType
    title: str
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    rules: Optional[str] = None
    start_at: datetime
    end_at: datetime
    status: OpenStatus
    reward_info: Optional[str] = None
    max_participants: Optional[int] = None
    scoring_config: Dict[str, float] = Field(default_factory=lambda: dict(DEFAULT_SCORING_CONFIG))
    participants_count: int = 0
    submissions_count: int = 0
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class JoinOpenResponse(BaseSchema):
    message: str = "Successfully joined Open"
    open_id: str
    user_id: str
    joined_at: Optional[datetime] = None


class SubmitSpreeRequest(BaseSchema):
    spree_id: str = Field(..., description="ID of the Spree to submit")

    @field_validator("spree_id")
    @classmethod
    def validate_spree_id(cls, v: str) -> str:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("spree_id cannot be empty.")
        return v


class OpenSubmissionResponse(BaseSchema):
    id: str
    open_id: str
    user_id: str
    spree_id: str
    score: float = 0.0
    rank: Optional[int] = None
    created_at: datetime


class OpenRankingItem(BaseSchema):
    rank: int
    score: float
    submission_id: str
    spree_id: str
    user_id: str
    creator_id: str
    creator: Optional[FeedCreatorInfo] = None
    spree: Optional[FeedSpreeResponse] = None
    spree_title: Optional[str] = None
    metrics: Optional[FeedEngagementMetrics] = None
    created_at: Optional[datetime] = None
