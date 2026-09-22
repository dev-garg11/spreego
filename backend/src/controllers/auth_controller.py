from typing import Optional
from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session
from src.models.user import User
from src.services.auth_service import AuthService
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


class AuthController:
    @staticmethod
    def send_otp(payload: SendOTPRequest, db: Session) -> SendOTPResponse:
        """Handle OTP dispatch."""
        try:
            identifier = payload.get_target_identifier()
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(err),
            )

        auth_service = AuthService(db)
        result = auth_service.send_otp(identifier)
        return SendOTPResponse(**result)

    @staticmethod
    def verify_otp(payload: VerifyOTPRequest, request: Request, db: Session) -> TokenResponse:
        """Handle OTP verification and token generation."""
        try:
            identifier = payload.get_target_identifier()
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(err),
            )

        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        auth_service = AuthService(db)
        try:
            result = auth_service.verify_otp(
                identifier=identifier,
                otp_code=payload.otp_code,
                ip_address=client_ip,
                user_agent=user_agent,
            )
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(err),
            )

        user_response = UserResponse.from_orm_model(result.get("user"))
        return TokenResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type=result.get("token_type", "bearer"),
            expires_in=result["expires_in"],
            user=user_response,
        )

    @staticmethod
    def refresh_token(payload: RefreshTokenRequest, request: Request, db: Session) -> TokenResponse:
        """Handle token rotation."""
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        auth_service = AuthService(db)
        try:
            result = auth_service.refresh_token(
                refresh_token=payload.refresh_token.strip(),
                ip_address=client_ip,
                user_agent=user_agent,
            )
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(err),
                headers={"WWW-Authenticate": "Bearer"},
            )

        return TokenResponse(**result)

    @staticmethod
    def logout(
        payload: Optional[LogoutRequest],
        current_user: User,
        db: Session,
    ) -> MessageResponse:
        """Handle user logout and session revocation."""
        if payload is not None and payload.refresh_token is not None:
            refresh_token = payload.refresh_token.strip()
        else:
            refresh_token = None

        auth_service = AuthService(db)
        result = auth_service.logout(user_id=current_user.id, refresh_token=refresh_token)
        return MessageResponse(**result)

    @staticmethod
    def get_me(current_user: User) -> UserResponse:
        """Return current user profile details."""
        res = UserResponse.from_orm_model(current_user)
        if not res:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        return res
