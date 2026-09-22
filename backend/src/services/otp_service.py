import hmac
import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from src.config.settings import settings
from src.models.otp import OTPCode
from src.repositories.otp_repository import OTPRepository
from src.utils.logger import log_mock_otp


class OTPService:
    def __init__(self, db: Session):
        self.db = db
        self.otp_repo = OTPRepository(db)

    def generate_code(self) -> str:
        """Generate cryptographically secure numeric OTP."""
        return "".join(secrets.choice("0123456789") for _ in range(settings.OTP_LENGTH))

    def send_otp(self, identifier: str) -> str:
        """Generate, store, and log mock OTP for the given identifier."""
        clean_identifier = identifier.strip()
        if "@" in clean_identifier:
            clean_identifier = clean_identifier.lower()
        
        # Atomically invalidate prior active OTPs without separate commit
        self.otp_repo.invalidate_all(clean_identifier, commit=False)

        otp_code = self.generate_code()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

        otp_entry = OTPCode(
            identifier=clean_identifier,
            otp_code=otp_code,
            expires_at=expires_at,
            is_used=False,
            attempts=0,
        )
        # Commit invalidation and new OTP together in a single transaction
        self.otp_repo.create(otp_entry)

        # Output mock OTP to console/stdout and logger
        log_mock_otp(clean_identifier, otp_code)

        return otp_code

    def verify_otp(self, identifier: str, input_code: str) -> bool:
        """Verify the provided OTP against the latest active OTP."""
        clean_identifier = identifier.strip()
        if "@" in clean_identifier:
            clean_identifier = clean_identifier.lower()
        clean_code = input_code.strip()

        otp_entry = self.otp_repo.get_latest_valid_otp(clean_identifier)
        if not otp_entry:
            raise ValueError("No active OTP found. Please request a new OTP.")

        if otp_entry.is_expired():
            self.otp_repo.mark_as_used(otp_entry)
            self.otp_repo.invalidate_all(clean_identifier)
            raise ValueError("OTP code has expired. Please request a new OTP.")

        if otp_entry.attempts >= settings.MAX_OTP_ATTEMPTS:
            self.otp_repo.mark_as_used(otp_entry)
            self.otp_repo.invalidate_all(clean_identifier)
            raise ValueError("Maximum OTP verification attempts exceeded. Please request a new OTP.")

        # Timing attack resistant comparison
        if not hmac.compare_digest(otp_entry.otp_code, clean_code):
            self.otp_repo.increment_attempts(otp_entry)
            remaining = settings.MAX_OTP_ATTEMPTS - otp_entry.attempts
            if remaining <= 0:
                self.otp_repo.mark_as_used(otp_entry)
                self.otp_repo.invalidate_all(clean_identifier)
            raise ValueError(f"Invalid OTP code. {max(remaining, 0)} attempt(s) remaining.")

        # Success - mark as used and clear any lingering OTPs
        self.otp_repo.mark_as_used(otp_entry)
        self.otp_repo.invalidate_all(clean_identifier)
        return True
