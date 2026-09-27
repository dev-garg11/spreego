import os
import shutil
from typing import List, Optional
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from src.config.settings import settings
from src.models.upload import Upload, UploadPurpose, UploadStatus
from src.repositories.upload_repository import UploadRepository
from src.services.storage_service import StorageService
from src.validations.upload_schemas import (
    ALLOWED_IMAGE_MIMES,
    ALLOWED_PURPOSE_MIMES,
    ALLOWED_VIDEO_MIMES,
    CompleteUploadResponse,
    PresignUploadRequest,
    PresignUploadResponse,
)


class UploadService:
    def __init__(self, db: Session, storage_service: Optional[StorageService] = None):
        self.db = db
        self.upload_repo = UploadRepository(db)
        self.storage_service = storage_service or StorageService()

    def _validate_purpose_and_type(self, purpose_str: str, content_type: str, file_size: int):
        try:
            purpose = UploadPurpose(purpose_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid purpose '{purpose_str}'. Allowed purposes: {[p.value for p in UploadPurpose]}",
            )

        content_type = content_type.lower().strip()
        allowed_mimes = ALLOWED_PURPOSE_MIMES.get(purpose, set())
        if content_type not in allowed_mimes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"MIME type '{content_type}' is not allowed for purpose '{purpose.value}'. Allowed: {sorted(list(allowed_mimes))}",
            )

        if purpose == UploadPurpose.SPREE_VIDEO:
            if file_size > settings.MAX_VIDEO_SIZE_BYTES:
                max_mb = settings.MAX_VIDEO_SIZE_BYTES // (1024 * 1024)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Video file exceeds maximum allowed size of {max_mb} MB.",
                )
        else:
            if file_size > settings.MAX_IMAGE_SIZE_BYTES:
                max_mb = settings.MAX_IMAGE_SIZE_BYTES // (1024 * 1024)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Image file exceeds maximum allowed size of {max_mb} MB.",
                )

        return purpose

    def prepare_presigned_upload(self, user_id: str, request: PresignUploadRequest) -> PresignUploadResponse:
        purpose = self._validate_purpose_and_type(
            purpose_str=request.purpose.value,
            content_type=request.content_type,
            file_size=request.file_size,
        )

        storage_key = self.storage_service.generate_storage_key(purpose.value, request.file_name)
        media_url = self.storage_service.get_public_url(storage_key)

        upload = self.upload_repo.create_upload(
            user_id=user_id,
            file_name=os.path.basename(storage_key),
            original_name=request.file_name,
            content_type=request.content_type.lower(),
            file_size=request.file_size,
            purpose=purpose.value,
            media_url=media_url,
            storage_path=storage_key,
            status=UploadStatus.PENDING,
        )

        upload_url = f"/api/v1/uploads/{upload.id}/file"

        return PresignUploadResponse(
            file_id=upload.id,
            upload_url=upload_url,
            media_url=media_url,
            method="POST",
            expires_in=3600,
            purpose=purpose.value,
            file_name=upload.file_name,
        )

    def upload_file_chunk(self, upload_id: str, user_id: str, file: UploadFile) -> CompleteUploadResponse:
        upload = self.upload_repo.get_by_id(upload_id)
        if not upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload session '{upload_id}' not found.",
            )

        if upload.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify this upload session.",
            )

        if file.content_type:
            cleaned_content_type = file.content_type.lower().strip()
            if cleaned_content_type != "application/octet-stream":
                if cleaned_content_type != upload.content_type:
                    purpose = UploadPurpose(upload.purpose)
                    if cleaned_content_type not in ALLOWED_PURPOSE_MIMES.get(purpose, set()):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Uploaded file MIME '{cleaned_content_type}' does not match expected '{upload.content_type}'",
                        )

        abs_path = self.storage_service.get_absolute_path(upload.storage_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        underlying_file = getattr(file, "file", file)
        if hasattr(underlying_file, "seek"):
            underlying_file.seek(0)

        with open(abs_path, "wb") as buffer:
            shutil.copyfileobj(underlying_file, buffer)

        actual_size = os.path.getsize(abs_path)

        if upload.purpose == UploadPurpose.SPREE_VIDEO.value:
            if actual_size > settings.MAX_VIDEO_SIZE_BYTES:
                self.storage_service.delete_file(upload.storage_path)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uploaded file exceeds video size limit.",
                )
        else:
            if actual_size > settings.MAX_IMAGE_SIZE_BYTES:
                self.storage_service.delete_file(upload.storage_path)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uploaded file exceeds image size limit.",
                )

        media_url = self.storage_service.get_public_url(upload.storage_path)
        updated = self.upload_repo.mark_completed(
            upload=upload,
            storage_path=upload.storage_path,
            media_url=media_url,
            actual_size=actual_size,
        )

        return CompleteUploadResponse(
            file_id=updated.id,
            status=updated.status.value,
            media_url=updated.media_url,
            file_name=updated.file_name,
            original_name=updated.original_name,
            content_type=updated.content_type,
            file_size=updated.file_size,
            purpose=updated.purpose,
        )

    def direct_upload(self, user_id: str, file: UploadFile, purpose_str: str) -> CompleteUploadResponse:
        content_type = (file.content_type or "application/octet-stream").lower().strip()
        filename = file.filename or "upload"

        purpose = self._validate_purpose_and_type(
            purpose_str=purpose_str,
            content_type=content_type,
            file_size=1,
        )

        storage_path, media_url, actual_size = self.storage_service.save_file(
            file=file,
            purpose=purpose.value,
            original_filename=filename,
        )

        if purpose == UploadPurpose.SPREE_VIDEO:
            if actual_size > settings.MAX_VIDEO_SIZE_BYTES:
                self.storage_service.delete_file(storage_path)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uploaded file exceeds video size limit.",
                )
        else:
            if actual_size > settings.MAX_IMAGE_SIZE_BYTES:
                self.storage_service.delete_file(storage_path)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uploaded file exceeds image size limit.",
                )

        upload = self.upload_repo.create_upload(
            user_id=user_id,
            file_name=os.path.basename(storage_path),
            original_name=filename,
            content_type=content_type,
            file_size=actual_size,
            purpose=purpose.value,
            media_url=media_url,
            storage_path=storage_path,
            status=UploadStatus.COMPLETED,
        )

        return CompleteUploadResponse(
            file_id=upload.id,
            status=upload.status.value,
            media_url=upload.media_url,
            file_name=upload.file_name,
            original_name=upload.original_name,
            content_type=upload.content_type,
            file_size=upload.file_size,
            purpose=upload.purpose,
        )

    def complete_upload(self, upload_id: str, user_id: str) -> CompleteUploadResponse:
        upload = self.upload_repo.get_by_id(upload_id)
        if not upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload session '{upload_id}' not found.",
            )

        if upload.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this upload session.",
            )

        if not upload.storage_path or not self.storage_service.file_exists(upload.storage_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File content has not been uploaded to storage yet.",
            )

        actual_size = self.storage_service.get_file_size(upload.storage_path)
        media_url = self.storage_service.get_public_url(upload.storage_path)
        updated = self.upload_repo.mark_completed(
            upload=upload,
            storage_path=upload.storage_path,
            media_url=media_url,
            actual_size=actual_size,
        )

        return CompleteUploadResponse(
            file_id=updated.id,
            status=updated.status.value,
            media_url=updated.media_url,
            file_name=updated.file_name,
            original_name=updated.original_name,
            content_type=updated.content_type,
            file_size=updated.file_size,
            purpose=updated.purpose,
        )

    def get_upload_by_id(self, upload_id: str, user_id: str) -> Upload:
        upload = self.upload_repo.get_by_id(upload_id)
        if not upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload record '{upload_id}' not found.",
            )
        if upload.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this upload record.",
            )
        return upload

    def get_user_uploads(self, user_id: str, page: int = 1, limit: int = 20) -> List[Upload]:
        skip = (page - 1) * limit
        return self.upload_repo.get_by_user(user_id=user_id, skip=skip, limit=limit)
