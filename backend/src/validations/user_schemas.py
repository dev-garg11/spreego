from typing import Optional
from pydantic import Field, field_validator
from src.validations.auth_schemas import BaseSchema


class UpdateProfileRequest(BaseSchema):
    full_name: Optional[str] = Field(None, max_length=128, description="User full name")
    username: Optional[str] = Field(None, max_length=64, description="Unique handle/username")
    bio: Optional[str] = Field(None, max_length=1000, description="User biography")
    avatar_url: Optional[str] = Field(None, max_length=512, description="Avatar image URL")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Username cannot be empty.")
        return v


class UserProfileResponse(BaseSchema):
    id: str
    username: Optional[str] = None
    full_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    followers_count: int = 0
    following_count: int = 0


class FollowUserItem(BaseSchema):
    id: str
    username: Optional[str] = None
    full_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
