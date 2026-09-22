from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


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

    def get_target_identifier(self) -> str:
        for val in (self.identifier, self.phone_number, self.email):
            if val is not None and str(val).strip():
                clean = str(val).strip()
                if "@" in clean:
                    return clean.lower()
                return clean
        raise ValueError("At least one of phone_number, email, or identifier is required.")


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
