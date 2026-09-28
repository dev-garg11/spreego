from datetime import datetime
from typing import Optional
from pydantic import Field, field_validator
from src.models.spree import SpreeType, SpreeVisibility
from src.validations.auth_schemas import BaseSchema


def _clean_tags_list(v) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        v = v.strip()
        if not v:
            return []
        if v.startswith("[") and v.endswith("]"):
            try:
                import json
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    v = parsed
            except Exception:
                pass
        if isinstance(v, str):
            v = [item.strip() for item in v.split(",") if item.strip()]
    if isinstance(v, (list, tuple, set)):
        cleaned: list[str] = []
        for item in v:
            if item is not None:
                t = str(item).strip().lower().lstrip("#").strip()[:100]
                if t and t not in cleaned:
                    cleaned.append(t)
        return cleaned[:50]
    return []


class CreateSpreeRequest(BaseSchema):
    type: SpreeType = Field(..., description="Spree content type: VIDEO_SHORT, VIDEO_LONG, PHOTO, SERIES")
    title: str = Field(..., max_length=255, description="Spree title")
    description: Optional[str] = Field(None, max_length=5000, description="Optional Spree description")
    media_url: str = Field(..., max_length=1024, description="Media URL")
    thumbnail_url: Optional[str] = Field(None, max_length=1024, description="Optional thumbnail image URL")
    duration: Optional[float] = Field(None, ge=0, description="Duration in seconds (optional for video)")
    visibility: SpreeVisibility = Field(default=SpreeVisibility.PUBLIC, description="Content visibility setting")
    category: Optional[str] = Field(None, max_length=100, description="Optional content category")
    tags: list[str] = Field(default_factory=list, description="Optional list of tag strings")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().lower().lstrip("#").strip()[:100]
            if not v:
                return None
        return v

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, v):
        return _clean_tags_list(v)

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Title cannot be empty.")
        return v

    @field_validator("media_url")
    @classmethod
    def validate_media_url(cls, v: str) -> str:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Media URL cannot be empty.")
        return v


    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v

    @field_validator("thumbnail_url")
    @classmethod
    def validate_thumbnail_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class UpdateSpreeRequest(BaseSchema):
    title: Optional[str] = Field(None, max_length=255, description="Updated title")
    description: Optional[str] = Field(None, max_length=5000, description="Updated description")
    media_url: Optional[str] = Field(None, max_length=1024, description="Updated media URL")
    thumbnail_url: Optional[str] = Field(None, max_length=1024, description="Updated thumbnail URL")
    duration: Optional[float] = Field(None, ge=0, description="Updated duration in seconds")
    visibility: Optional[SpreeVisibility] = Field(None, description="Updated visibility setting")
    category: Optional[str] = Field(None, max_length=100, description="Updated category")
    tags: Optional[list[str]] = Field(None, description="Updated tags")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().lower().lstrip("#").strip()[:100]
            if not v:
                return None
        return v

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, v):
        return _clean_tags_list(v)

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            raise ValueError("Title cannot be null.")
        v = v.strip()
        if not v:
            raise ValueError("Title cannot be empty.")
        return v

    @field_validator("media_url")
    @classmethod
    def validate_media_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            raise ValueError("Media URL cannot be null.")
        v = v.strip()
        if not v:
            raise ValueError("Media URL cannot be empty.")
        return v

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, v: Optional[SpreeVisibility]) -> Optional[SpreeVisibility]:
        if v is None:
            raise ValueError("Visibility cannot be null.")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v

    @field_validator("thumbnail_url")
    @classmethod
    def validate_thumbnail_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class SpreeResponse(BaseSchema):
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

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, v):
        return _clean_tags_list(v)

