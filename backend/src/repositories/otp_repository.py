from typing import Optional
from sqlalchemy.orm import Session
from src.models.otp import OTPCode
from src.repositories.base_repository import BaseRepository


class OTPRepository(BaseRepository[OTPCode]):
    def __init__(self, db: Session):
        super().__init__(OTPCode, db)

    def invalidate_older_active_otps(self, identifier: str, latest_id: str) -> int:
        """Invalidate any older overlapping active OTPs for the identifier to eliminate race conditions."""
        clean = identifier.strip().lower() if "@" in identifier else identifier.strip()
        try:
            count = (
                self.db.query(OTPCode)
                .filter(
                    OTPCode.identifier == clean,
                    OTPCode.id != latest_id,
                    OTPCode.is_used.is_(False),
                )
                .update({"is_used": True}, synchronize_session="fetch")
            )
            if count > 0:
                self.db.commit()
            return count
        except Exception:
            self.db.rollback()
            raise

    def get_latest_valid_otp(self, identifier: str) -> Optional[OTPCode]:
        clean = identifier.strip().lower() if "@" in identifier else identifier.strip()
        latest = (
            self.db.query(OTPCode)
            .filter(
                OTPCode.identifier == clean,
                OTPCode.is_used.is_(False),
            )
            .order_by(OTPCode.created_at.desc(), OTPCode.id.desc())
            .first()
        )
        if latest:
            self.invalidate_older_active_otps(clean, latest.id)
        return latest

    def invalidate_all(self, identifier: str, commit: bool = True) -> int:
        clean = identifier.strip().lower() if "@" in identifier else identifier.strip()
        try:
            count = (
                self.db.query(OTPCode)
                .filter(OTPCode.identifier == clean, OTPCode.is_used.is_(False))
                .update({"is_used": True}, synchronize_session="fetch")
            )
            if commit:
                self.db.commit()
            return count
        except Exception:
            self.db.rollback()
            raise

    def mark_as_used(self, otp: OTPCode) -> OTPCode:
        try:
            otp.is_used = True
            self.db.commit()
            self.db.refresh(otp)
            return otp
        except Exception:
            self.db.rollback()
            raise

    def increment_attempts(self, otp: OTPCode) -> OTPCode:
        try:
            otp.attempts += 1
            self.db.commit()
            self.db.refresh(otp)
            return otp
        except Exception:
            self.db.rollback()
            raise
