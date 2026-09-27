from datetime import datetime
from typing import Optional
from pydantic import Field, field_validator
from src.models.moderation import ReportEntityType, ReportReason, ReportStatus
from src.validations.auth_schemas import BaseSchema


class CreateReportRequest(BaseSchema):
    entity_id: str = Field(..., min_length=1, max_length=255, description="ID of reported entity")
    entity_type: ReportEntityType = Field(..., description="Type of entity")
    reason: ReportReason = Field(..., description="Reason for reporting")
    description: Optional[str] = Field(None, max_length=2000, description="Optional description")

    @field_validator("entity_id")
    @classmethod
    def validate_entity_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("entity_id cannot be blank.")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            stripped = v.strip()
            return stripped if stripped else None
        return None


class ReportResponse(BaseSchema):
    id: str
    reporter_id: str
    entity_id: str
    entity_type: ReportEntityType
    reason: ReportReason
    description: Optional[str] = None
    status: ReportStatus
    created_at: datetime


class BlockResponse(BaseSchema):
    id: Optional[str] = None
    blocker_id: str
    blocked_id: str
    created_at: Optional[datetime] = None
    message: str = "User blocked successfully."


class MuteResponse(BaseSchema):
    id: Optional[str] = None
    muter_id: str
    muted_id: str
    created_at: Optional[datetime] = None
    message: str = "User muted successfully."


class BlockedUserItem(BaseSchema):
    id: str
    user_id: str
    blocked_id: str
    username: Optional[str] = None
    full_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None


class MutedUserItem(BaseSchema):
    id: str
    user_id: str
    muted_id: str
    username: Optional[str] = None
    full_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None
