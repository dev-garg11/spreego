from datetime import datetime
from typing import Optional
from pydantic import Field, field_validator
from src.validations.auth_schemas import BaseSchema, MessageResponse


class RecordViewRequest(BaseSchema):
    watch_duration: float = Field(0.0, ge=0, allow_inf_nan=False, description="Watch duration in seconds")
    completed: bool = Field(False, description="Whether the spree watch was completed")


class ViewResponse(BaseSchema):
    message: str = "View recorded successfully."
    id: str
    spree_id: str
    user_id: Optional[str] = None
    watch_duration: float = 0.0
    completed: bool = False
    created_at: Optional[datetime] = None


class ClapResponse(MessageResponse):
    message: str = "Spree clapped successfully."
    clapped: bool = True


class UnclapResponse(MessageResponse):
    message: str = "Clap removed successfully."
    clapped: bool = False


class CreateCommentRequest(BaseSchema):
    text: str = Field(..., min_length=1, max_length=2000, description="Comment text content")
    parent_id: Optional[str] = Field(None, max_length=36, description="Optional parent comment ID for replies")

    @field_validator("text", mode="before")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if v is not None and isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Comment text cannot be empty.")
        return v

    @field_validator("parent_id", mode="before")
    @classmethod
    def validate_parent_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and isinstance(v, str):
            v = v.strip()
            if not v:
                return None
        return v


class CommentUserProfile(BaseSchema):
    id: str
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    full_name: Optional[str] = None


class CommentResponse(BaseSchema):
    id: str
    spree_id: str
    user_id: str
    text: str
    parent_id: Optional[str] = None
    created_at: Optional[datetime] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    user: Optional[CommentUserProfile] = None


class RecordShareRequest(BaseSchema):
    platform: Optional[str] = Field(None, max_length=64, description="Sharing platform, e.g. whatsapp, twitter")

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class ShareResponse(BaseSchema):
    message: str = "Spree shared successfully."
    id: str
    spree_id: str
    user_id: Optional[str] = None
    platform: Optional[str] = None
    share_count: int = 0
    created_at: Optional[datetime] = None


class SaveResponse(MessageResponse):
    message: str = "Spree saved successfully."
    saved: bool = True


class UnsaveResponse(MessageResponse):
    message: str = "Spree unsaved successfully."
    saved: bool = False
