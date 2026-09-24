from typing import List
from fastapi import UploadFile
from sqlalchemy.orm import Session
from src.services.upload_service import UploadService
from src.validations.upload_schemas import (
    CompleteUploadResponse,
    PresignUploadRequest,
    PresignUploadResponse,
    UploadItemResponse,
)


class UploadController:
    def __init__(self, db: Session):
        self.upload_service = UploadService(db)

    def presign_upload(self, user_id: str, request: PresignUploadRequest) -> PresignUploadResponse:
        return self.upload_service.prepare_presigned_upload(user_id=user_id, request=request)

    def upload_file(self, upload_id: str, user_id: str, file: UploadFile) -> CompleteUploadResponse:
        return self.upload_service.upload_file_chunk(upload_id=upload_id, user_id=user_id, file=file)

    def direct_upload(self, user_id: str, file: UploadFile, purpose: str) -> CompleteUploadResponse:
        return self.upload_service.direct_upload(user_id=user_id, file=file, purpose_str=purpose)

    def complete_upload(self, upload_id: str, user_id: str) -> CompleteUploadResponse:
        return self.upload_service.complete_upload(upload_id=upload_id, user_id=user_id)

    def get_upload(self, upload_id: str, user_id: str) -> UploadItemResponse:
        upload = self.upload_service.get_upload_by_id(upload_id=upload_id, user_id=user_id)
        return UploadItemResponse(
            id=upload.id,
            file_name=upload.file_name,
            original_name=upload.original_name,
            content_type=upload.content_type,
            file_size=upload.file_size,
            purpose=upload.purpose,
            status=upload.status.value,
            media_url=upload.media_url,
            created_at=upload.created_at.isoformat(),
            completed_at=upload.completed_at.isoformat() if upload.completed_at else None,
        )

    def get_my_uploads(self, user_id: str, page: int, limit: int) -> List[UploadItemResponse]:
        uploads = self.upload_service.get_user_uploads(user_id=user_id, page=page, limit=limit)
        return [
            UploadItemResponse(
                id=u.id,
                file_name=u.file_name,
                original_name=u.original_name,
                content_type=u.content_type,
                file_size=u.file_size,
                purpose=u.purpose,
                status=u.status.value,
                media_url=u.media_url,
                created_at=u.created_at.isoformat(),
                completed_at=u.completed_at.isoformat() if u.completed_at else None,
            )
            for u in uploads
        ]
