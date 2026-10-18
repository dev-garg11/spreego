from datetime import datetime
import re
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SendOTPRequest(BaseSchema):
    phone_number: Optional[str] = Field(None, description="E.164 phone number, e.g. +1234567890")
    email: Optional[str] = Field(None, description="User email address")
    identifier: Optional[str] = Field(None, description="General contact identifier")

    def get_target_identifier(self) -> str:
        for val in (self.identifier, self.phone_number, self.email):
            if val is not None and str(val).strip():
                clean = str(val).strip()
                if "@" in clean:
                    return clean.lower()
                return clean
        raise ValueError("At least one of phone_number, email, or identifier is required.")


class VerifyOTPRequest(BaseSchema):
    phone_number: Optional[str] = Field(None, description="E.164 phone number, e.g. +1234567890")
    email: Optional[str] = Field(None, description="User email address")
    identifier: Optional[str] = Field(None, description="General contact identifier")
    otp_code: str = Field(..., min_length=4, max_length=10, description="4-10 digit OTP code")
    full_name: Optional[str] = Field(None, min_length=2, max_length=128, description="Display name for new registrations")
    username: Optional[str] = Field(None, min_length=3, max_length=64, description="Unique username for new registrations")

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Full name must contain at least 2 characters.")
        return value

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip().lstrip("@").lower()
        if not re.fullmatch(r"[a-z0-9_\.]{3,64}", value):
            raise ValueError("Username may contain only lowercase letters, numbers, underscores, and dots.")
        return value

    def get_target_identifier(self) -> str:
        for val in (self.identifier, self.phone_number, self.email):
            if val is not None and str(val).strip():
                clean = str(val).strip()
                if "@" in clean:
                    return clean.lower()
                return clean
        raise ValueError("At least one of phone_number, email, or identifier is required.")


class RegisterRequest(BaseSchema):
    identifier: str = Field(..., min_length=3, max_length=255, description="Email address or phone number")
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=128)

    @field_validator("identifier", "username", "full_name")
    @classmethod
    def trim_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty.")
        return value

    @field_validator("username")
    @classmethod
    def validate_registration_username(cls, value: str) -> str:
        value = value.lstrip("@").lower()
        if not re.fullmatch(r"[a-z0-9_\.]{3,64}", value):
            raise ValueError("Username may contain only letters, numbers, underscores, and dots.")
        return value


class LoginRequest(BaseSchema):
    identifier: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("identifier")
    @classmethod
    def trim_login_identifier(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Username, email, or phone is required.")
        return value


class ForgotPasswordRequest(BaseSchema):
    identifier: str = Field(..., min_length=3, max_length=255)

    @field_validator("identifier")
    @classmethod
    def trim_reset_identifier(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Username, email, or phone is required.")
        return value


class ResetPasswordRequest(BaseSchema):
    identifier: str = Field(..., min_length=3, max_length=255)
    otp_code: str = Field(..., min_length=4, max_length=10)
    new_password: str = Field(..., min_length=8, max_length=128)


class RefreshTokenRequest(BaseSchema):
    refresh_token: str = Field(..., description="Valid JWT refresh token")


class LogoutRequest(BaseSchema):
    refresh_token: Optional[str] = Field(None, description="Optional specific refresh token to revoke")


class ProfileResponse(BaseSchema):
    id: str
    user_id: str
    full_name: Optional[str] = None
    username: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UserResponse(BaseSchema):
    id: str
    phone_number: Optional[str] = None
    email: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    profile: Optional[ProfileResponse] = None

    @classmethod
    def from_orm_model(cls, user: Any) -> Optional["UserResponse"]:
        if user is None:
            return None
        profile_data = None
        if hasattr(user, "profile") and user.profile:
            p = user.profile
            profile_data = ProfileResponse(
                id=str(p.id),
                user_id=str(p.user_id),
                full_name=p.full_name,
                username=p.username,
                bio=p.bio,
                avatar_url=p.avatar_url,
                created_at=p.created_at,
                updated_at=getattr(p, "updated_at", None),
            )
        return cls(
            id=str(user.id),
            phone_number=user.phone_number,
            email=user.email,
            is_active=bool(user.is_active),
            is_verified=bool(user.is_verified),
            created_at=user.created_at,
            updated_at=getattr(user, "updated_at", None),
            profile=profile_data,
        )


class TokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Optional[UserResponse] = None


class SendOTPResponse(BaseSchema):
    message: str
    identifier: str


class MessageResponse(BaseSchema):
    message: str
    detail: Optional[str] = None
