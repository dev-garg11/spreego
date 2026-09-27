import os
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class UploadPurpose(str, Enum):
    SPREE_VIDEO = "spree_video"
    SPREE_THUMBNAIL = "spree_thumbnail"
    PRODUCT_IMAGE = "product_image"
    AVATAR = "avatar"
    OPEN_COVER = "open_cover"


ALLOWED_IMAGE_MIMES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}

ALLOWED_VIDEO_MIMES = {
    "video/mp4",
    "video/quicktime",
    "video/webm",
    "video/x-matroska",
    "video/mpeg",
}

ALLOWED_PURPOSE_MIMES = {
    UploadPurpose.SPREE_VIDEO: ALLOWED_VIDEO_MIMES,
    UploadPurpose.SPREE_THUMBNAIL: ALLOWED_IMAGE_MIMES,
    UploadPurpose.PRODUCT_IMAGE: ALLOWED_IMAGE_MIMES,
    UploadPurpose.AVATAR: ALLOWED_IMAGE_MIMES,
    UploadPurpose.OPEN_COVER: ALLOWED_IMAGE_MIMES,
}


class PresignUploadRequest(BaseModel):
    file_name: str = Field(..., min_length=1, max_length=255, description="Original filename with extension")
    content_type: str = Field(..., min_length=3, max_length=100, description="MIME type of the file")
    file_size: int = Field(..., gt=0, description="File size in bytes")
    purpose: UploadPurpose = Field(..., description="Target purpose for this media asset")

    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, v: str) -> str:
        clean = os.path.basename(v).strip()
        if not clean or "." not in clean:
            raise ValueError("File name must include a valid extension")
        return clean

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in ALLOWED_IMAGE_MIMES and clean not in ALLOWED_VIDEO_MIMES:
            raise ValueError(f"Unsupported MIME type '{clean}'. Allowed types: images or videos.")
        return clean


class PresignUploadResponse(BaseModel):
    file_id: str
    upload_url: str
    media_url: str
    method: str = "POST"
    expires_in: int = 3600
    purpose: str
    file_name: str


class CompleteUploadResponse(BaseModel):
    file_id: str
    status: str
    media_url: str
    file_name: str
    original_name: str
    content_type: str
    file_size: int
    purpose: str


class UploadItemResponse(BaseModel):
    id: str
    file_name: str
    original_name: str
    content_type: str
    file_size: int
    purpose: str
    status: str
    media_url: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
