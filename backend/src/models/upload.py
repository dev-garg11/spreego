import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from src.config.database import Base


class UploadStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class UploadPurpose(str, enum.Enum):
    SPREE_VIDEO = "spree_video"
    SPREE_THUMBNAIL = "spree_thumbnail"
    PRODUCT_IMAGE = "product_image"
    AVATAR = "avatar"
    OPEN_COVER = "open_cover"


class Upload(Base):
    __tablename__ = "uploads"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False, default=0)
    purpose = Column(String(50), nullable=False)
    status = Column(Enum(UploadStatus), default=UploadStatus.PENDING, nullable=False, index=True)
    storage_path = Column(String(500), nullable=True)
    media_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", backref="uploads", lazy="select")

    def __repr__(self) -> str:
        return f"<Upload(id='{self.id}', file_name='{self.file_name}', status='{self.status}')>"
