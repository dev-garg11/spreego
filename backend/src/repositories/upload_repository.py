from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from src.models.upload import Upload, UploadStatus
from src.repositories.base_repository import BaseRepository


class UploadRepository(BaseRepository[Upload]):
    def __init__(self, db: Session):
        super().__init__(Upload, db)

    def create_upload(
        self,
        user_id: str,
        file_name: str,
        original_name: str,
        content_type: str,
        file_size: int,
        purpose: str,
        media_url: Optional[str] = None,
        storage_path: Optional[str] = None,
        status: UploadStatus = UploadStatus.PENDING,
    ) -> Upload:
        upload = Upload(
            user_id=user_id,
            file_name=file_name,
            original_name=original_name,
            content_type=content_type,
            file_size=file_size,
            purpose=purpose,
            media_url=media_url,
            storage_path=storage_path,
            status=status,
            completed_at=datetime.now(timezone.utc) if status == UploadStatus.COMPLETED else None,
        )
        return self.create(upload)

    def mark_completed(
        self,
        upload: Upload,
        storage_path: str,
        media_url: str,
        actual_size: Optional[int] = None,
    ) -> Upload:
        upload.storage_path = storage_path
        upload.media_url = media_url
        if actual_size is not None and actual_size > 0:
            upload.file_size = actual_size
        upload.status = UploadStatus.COMPLETED
        upload.completed_at = datetime.now(timezone.utc)
        return self.update(upload)

    def mark_failed(self, upload: Upload) -> Upload:
        upload.status = UploadStatus.FAILED
        return self.update(upload)

    def get_by_user(self, user_id: str, skip: int = 0, limit: int = 50) -> List[Upload]:
        return (
            self.db.query(Upload)
            .filter(Upload.user_id == user_id)
            .order_by(Upload.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
