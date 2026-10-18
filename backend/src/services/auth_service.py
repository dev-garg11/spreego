import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from src.config.passwords import hash_password, verify_password
from src.config.security import TokenError, decode_token
from src.models.profile import Profile
from src.models.user import User
from src.repositories.profile_repository import ProfileRepository
from src.repositories.user_repository import UserRepository
from src.services.otp_service import OTPService
from src.services.token_service import TokenService


class LoginLockedError(ValueError):
    def __init__(self, retry_after_seconds: int):
        self.retry_after_seconds = max(1, retry_after_seconds)
        super().__init__(f"Too many incorrect password attempts. Try again in {self.retry_after_seconds // 60 + 1} minute(s).")


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

    @staticmethod
    def _normalize_login_identifier(identifier: str) -> str:
        clean = identifier.strip()
        return clean.lower() if "@" in clean or clean.startswith("@") else clean

    def _find_login_user(self, identifier: str) -> Optional[User]:
        clean = self._normalize_login_identifier(identifier)
        if clean.startswith("@") or ("@" not in clean and not clean.replace("+", "").isdigit()):
            return self.user_repo.get_by_username(clean)
        return self.user_repo.get_by_identifier(clean)

    def register_password_user(
        self,
        identifier: str,
        username: str,
        password: str,
        full_name: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        clean_identifier = self._normalize_login_identifier(identifier)
        clean_username = username.strip().lstrip("@").lower()
        if self.user_repo.get_by_identifier(clean_identifier):
            raise ValueError("An account with this email or phone already exists.")
        if self.profile_repo.get_by_username(clean_username):
            raise ValueError("Username already taken. Choose another handle.")

        is_email = "@" in clean_identifier
        user = User(
            phone_number=None if is_email else clean_identifier,
            email=clean_identifier if is_email else None,
            password_hash=hash_password(password),
            is_active=True,
            is_verified=True,
        )
        try:
            self.db.add(user)
            self.db.flush()
            self.db.add(Profile(user_id=user.id, username=clean_username, full_name=full_name.strip()))
            self.db.commit()
            self.db.refresh(user)
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Username is already taken. Choose another handle.")

        user = self.user_repo.get_by_id(user.id)
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

    def login_password_user(
        self,
        identifier: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        user = self._find_login_user(identifier)
        if not user or not user.is_active or not verify_password(password, user.password_hash):
            if user and user.is_active:
                user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
                if user.failed_login_attempts >= 4:
                    user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
                self.user_repo.update(user)
                if user.locked_until:
                    raise LoginLockedError(15 * 60)
                remaining = max(0, 4 - user.failed_login_attempts)
                raise ValueError(f"Incorrect password. {remaining} attempt(s) remaining.")
            raise ValueError("Incorrect username, email, phone, or password.")

        now = datetime.now(timezone.utc)
        if user.locked_until:
            locked_until = user.locked_until.replace(tzinfo=timezone.utc) if user.locked_until.tzinfo is None else user.locked_until
            if locked_until > now:
                raise LoginLockedError(int((locked_until - now).total_seconds()))
            user.locked_until = None

        user.failed_login_attempts = 0
        user.locked_until = None
        self.user_repo.update(user)
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

    def request_password_reset(self, identifier: str) -> Dict[str, str]:
        user = self._find_login_user(identifier)
        # Keep the response generic so the endpoint cannot enumerate accounts.
        if user and user.is_active:
            target = user.email or user.phone_number
            if target:
                self.otp_service.send_otp(target)
        return {"message": "If an account exists, a reset code has been sent."}

    def reset_password(self, identifier: str, otp_code: str, new_password: str) -> Dict[str, str]:
        user = self._find_login_user(identifier)
        if not user or not user.is_active:
            raise ValueError("Invalid reset request.")
        target = user.email or user.phone_number
        if not target:
            raise ValueError("This account cannot use password reset.")
        self.otp_service.verify_otp(target, otp_code)
        user.password_hash = hash_password(new_password)
        user.failed_login_attempts = 0
        user.locked_until = None
        self.user_repo.update(user)
        return {"message": "Password reset successfully. You can log in now."}

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
        full_name: Optional[str] = None,
        username: Optional[str] = None,
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

        # Apply registration profile details after the account exists. Login requests
        # leave these values unset, while registration can claim a unique handle.
        if full_name is not None or username is not None:
            profile = self.profile_repo.get_by_user_id(user.id)
            if profile is None:
                profile = Profile(user_id=user.id)
            if username is not None:
                existing_profile = self.profile_repo.get_by_username(username)
                if existing_profile and existing_profile.user_id != user.id:
                    raise ValueError("Username already taken.")
                profile.username = username
            if full_name is not None:
                profile.full_name = full_name.strip()
            self.profile_repo.update(profile)
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
