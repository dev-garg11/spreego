import re
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from src.config.security import TokenError, decode_token
from src.models.profile import Profile
from src.models.user import User
from src.repositories.profile_repository import ProfileRepository
from src.repositories.user_repository import UserRepository
from src.services.otp_service import OTPService
from src.services.token_service import TokenService


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.profile_repo = ProfileRepository(db)
        self.otp_service = OTPService(db)
        self.token_service = TokenService(db)

    def send_otp(self, identifier: str) -> Dict[str, str]:
        """Send OTP to identifier (phone or email)."""
        clean_identifier = identifier.strip()
        if "@" in clean_identifier:
            clean_identifier = clean_identifier.lower()
        self.otp_service.send_otp(clean_identifier)
        return {
            "message": "OTP sent successfully.",
            "identifier": clean_identifier,
        }

    def _generate_default_username(self, clean_identifier: str, user_id: str, is_email: bool) -> str:
        """Generate collision-safe and sanitized username."""
        unique_suffix = str(user_id).replace("-", "")[:8]
        if is_email:
            raw_prefix = clean_identifier.split("@")[0]
            sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", raw_prefix)[:20].strip("_")
            if not sanitized:
                sanitized = "user"
            base_username = f"{sanitized}_{unique_suffix}"
        else:
            base_username = f"user_{unique_suffix}"

        candidate_username = base_username
        counter = 1
        while self.profile_repo.get_by_username(candidate_username):
            candidate_username = f"{base_username}_{counter}"
            counter += 1
        return candidate_username

    def verify_otp(
        self,
        identifier: str,
        otp_code: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Verify OTP and authenticate or register user."""
        clean_identifier = identifier.strip()
        if "@" in clean_identifier:
            clean_identifier = clean_identifier.lower()
        
        # Verify OTP code
        self.otp_service.verify_otp(clean_identifier, otp_code)

        # Look up existing user
        user = self.user_repo.get_by_identifier(clean_identifier)
        is_email = "@" in clean_identifier

        if not user:
            # Register new user
            user = User(
                phone_number=clean_identifier if not is_email else None,
                email=clean_identifier if is_email else None,
                is_active=True,
                is_verified=True,
            )
            user = self.user_repo.create(user)

            # Create default profile with collision-safe and sanitized username
            candidate_username = self._generate_default_username(clean_identifier, user.id, is_email)
            profile = Profile(
                user=user,
                user_id=user.id,
                username=candidate_username,
                full_name=None,
            )
            self.profile_repo.create(profile)
            # Re-fetch user with loaded profile
            user = self.user_repo.get_by_id(user.id)
        else:
            if not user.is_active:
                raise ValueError("User account is inactive.")
            user.is_verified = True
            self.user_repo.update(user)

            # Self-heal missing profile if user previously had none
            if not user.profile:
                candidate_username = self._generate_default_username(clean_identifier, user.id, is_email)
                profile = Profile(
                    user=user,
                    user_id=user.id,
                    username=candidate_username,
                    full_name=None,
                )
                self.profile_repo.create(profile)
                user = self.user_repo.get_by_id(user.id)

        # Issue tokens and record session
        access_token, refresh_token, expires_in = self.token_service.create_auth_tokens(
            user_id=user.id,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": expires_in,
            "user": user,
        }

    def refresh_token(
        self,
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Refresh JWT tokens using valid refresh token."""
        try:
            payload = decode_token(refresh_token)
            user_id = payload.get("sub")
            if user_id:
                user = self.user_repo.get_by_id(user_id)
                if not user:
                    raise ValueError("User not found.")
                if not user.is_active:
                    raise ValueError("User account is inactive.")
        except TokenError:
            pass  # Let rotate_refresh_token handle token decoding error

        access_token, new_refresh_token, expires_in = self.token_service.rotate_refresh_token(
            old_refresh_token=refresh_token,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": expires_in,
        }

    def logout(self, user_id: str, refresh_token: Optional[str] = None) -> Dict[str, str]:
        """Revoke session(s) for user."""
        if refresh_token is not None:
            self.token_service.revoke_token(refresh_token, user_id=user_id)
        else:
            self.token_service.revoke_all_sessions(user_id)

        return {"message": "Logged out successfully."}

    def get_me(self, user_id: str) -> User:
        """Fetch authenticated user details."""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found.")
        if not user.is_active:
            raise ValueError("User account is inactive.")
        if not user.profile:
            # Self-heal missing profile
            clean_ident = user.email or user.phone_number or "user"
            candidate_username = self._generate_default_username(clean_ident, user.id, is_email="@" in clean_ident)
            profile = Profile(
                user=user,
                user_id=user.id,
                username=candidate_username,
                full_name=None,
            )
            self.profile_repo.create(profile)
            user = self.user_repo.get_by_id(user.id)
        return user
