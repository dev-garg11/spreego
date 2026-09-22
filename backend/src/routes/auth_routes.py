from typing import Optional
from fastapi import APIRouter, Body, Depends, Request, status
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.auth_controller import AuthController
from src.middlewares.auth_middleware import get_current_user
from src.models.user import User
from src.validations.auth_schemas import (
    LogoutRequest,
    MessageResponse,
    RefreshTokenRequest,
    SendOTPRequest,
    SendOTPResponse,
    TokenResponse,
    UserResponse,
    VerifyOTPRequest,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/send-otp",
    response_model=SendOTPResponse,
    status_code=status.HTTP_200_OK,
    summary="Send OTP to phone or email",
)
def send_otp(
    payload: SendOTPRequest,
    db: Session = Depends(get_db),
) -> SendOTPResponse:
    """Dispatches a mock 6-digit OTP to the provided phone number or email."""
    return AuthController.send_otp(payload=payload, db=db)


@router.post(
    "/verify-otp",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify OTP and receive JWT tokens",
)
def verify_otp(
    payload: VerifyOTPRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Verifies OTP, provisions or activates user, and returns JWT access/refresh tokens."""
    return AuthController.verify_otp(payload=payload, request=request, db=db)


@router.post(
    "/refresh-token",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate refresh token for new access token",
)
def refresh_token(
    payload: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Rotates refresh token and returns new access/refresh token pair."""
    return AuthController.refresh_token(payload=payload, request=request, db=db)


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke session and log out",
)
def logout(
    payload: Optional[LogoutRequest] = Body(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Revokes active user session(s)."""
    return AuthController.logout(payload=payload, current_user=current_user, db=db)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Returns profile and account status for current authenticated user."""
    return AuthController.get_me(current_user=current_user)
