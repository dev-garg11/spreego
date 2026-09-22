import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from src.config.database import Base


class OTPCode(Base):
    __tablename__ = "otp_codes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    identifier = Column(String(255), nullable=False, index=True)
    otp_code = Column(String(16), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False, nullable=False, index=True)
    attempts = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    def is_expired(self) -> bool:
        current_time = datetime.now(timezone.utc)
        # Ensure offset-aware comparison
        target_expiry = (
            self.expires_at.replace(tzinfo=timezone.utc)
            if self.expires_at.tzinfo is None
            else self.expires_at
        )
        return current_time > target_expiry

    def __repr__(self) -> str:
        return f"<OTPCode(id='{self.id}', identifier='{self.identifier}', is_used={self.is_used})>"
