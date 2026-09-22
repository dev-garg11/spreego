from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from src.config.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    TokenError,
)
from src.config.settings import settings
from src.models.user_session import UserSession
from src.repositories.session_repository import SessionRepository


class TokenService:
    def __init__(self, db: Session):
        self.db = db
        self.session_repo = SessionRepository(db)

    def create_auth_tokens(
        self,
        user_id: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Tuple[str, str, int]:
        """
        Create access token and refresh token, recording the session.
        Returns: (access_token, refresh_token, expires_in_seconds)
        """
        access_token = create_access_token(user_id=user_id)
        refresh_token = create_refresh_token(user_id=user_id)
        
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        session = UserSession(
            user_id=user_id,
            refresh_token=refresh_token,
            user_agent=user_agent[:500] if user_agent else None,
            ip_address=ip_address[:64] if ip_address else None,
            is_revoked=False,
            expires_at=expires_at,
        )
        self.session_repo.create(session)

        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        return access_token, refresh_token, expires_in

    def rotate_refresh_token(
        self,
        old_refresh_token: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Tuple[str, str, int]:
        """
        Validate existing refresh token, revoke it, and issue a new pair.
        Returns: (new_access_token, new_refresh_token, expires_in_seconds)
        """
        try:
            payload = decode_token(old_refresh_token)
        except TokenError as exc:
            raise ValueError(f"Invalid refresh token: {str(exc)}")

        token_type = payload.get("type")
        if token_type != "refresh":
            raise ValueError("Provided token is not a refresh token.")

        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Token missing user subject.")

        # Check DB session
        db_session = self.session_repo.get_by_refresh_token(old_refresh_token)
        if not db_session or db_session.is_revoked:
            raise ValueError("Refresh token is invalid or has been revoked.")

        if str(db_session.user_id) != str(user_id):
            raise ValueError("Refresh token user mismatch.")

        now_utc = datetime.now(timezone.utc)
        session_exp = (
            db_session.expires_at.replace(tzinfo=timezone.utc)
            if db_session.expires_at.tzinfo is None
            else db_session.expires_at
        )
        is_expired = now_utc > session_exp

        if is_expired:
            try:
                db_session.is_revoked = True
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise
            raise ValueError("Refresh token session has expired.")

        # Stage revocation of old session (Rotation policy)
        db_session.is_revoked = True

        # Issue new token pair and commit revocation + new session atomically
        return self.create_auth_tokens(
            user_id=user_id,
            user_agent=user_agent or db_session.user_agent,
            ip_address=ip_address or db_session.ip_address,
        )

    def revoke_token(self, refresh_token: str, user_id: Optional[str] = None) -> bool:
        """Revoke a specific session by refresh token."""
        return self.session_repo.revoke_by_token(refresh_token, user_id=user_id)

    def revoke_all_sessions(self, user_id: str) -> int:
        """Revoke all sessions for a user."""
        return self.session_repo.revoke_all_for_user(user_id)
