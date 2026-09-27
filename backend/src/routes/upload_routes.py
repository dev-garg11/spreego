from typing import List
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.upload_controller import UploadController
from src.middlewares.auth_middleware import get_current_user
from src.models.user import User
from src.validations.upload_schemas import (
    CompleteUploadResponse,
    PresignUploadRequest,
    PresignUploadResponse,
    UploadItemResponse,
)

router = APIRouter(prefix="/api/v1/uploads", tags=["Uploads"])


@router.post(
    "/presign",
    response_model=PresignUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate presigned upload endpoint and metadata",
)
def presign_upload(
    payload: PresignUploadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    controller = UploadController(db)
    return controller.presign_upload(user_id=current_user.id, request=payload)


@router.post(
    "/direct",
    response_model=CompleteUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="One-step direct file upload for development & mobile clients",
)
def direct_upload(
    file: UploadFile = File(...),
    purpose: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    controller = UploadController(db)
    return controller.direct_upload(user_id=current_user.id, file=file, purpose=purpose)


@router.post(
    "/{file_id}/file",
    response_model=CompleteUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload binary file chunk for a presigned upload session",
)
def upload_file_content(
    file_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    controller = UploadController(db)
    return controller.upload_file(upload_id=file_id, user_id=current_user.id, file=file)


@router.post(
    "/{file_id}/complete",
    response_model=CompleteUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm completion and availability of an upload session",
)
def complete_upload(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    controller = UploadController(db)
    return controller.complete_upload(upload_id=file_id, user_id=current_user.id)


@router.get(
    "/my",
    response_model=List[UploadItemResponse],
    status_code=status.HTTP_200_OK,
    summary="List authenticated user's uploaded assets",
)
def get_my_uploads(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    controller = UploadController(db)
    return controller.get_my_uploads(user_id=current_user.id, page=page, limit=limit)


@router.get(
    "/{file_id}",
    response_model=UploadItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Lookup metadata for an uploaded asset",
)
def get_upload_details(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    controller = UploadController(db)
    return controller.get_upload(upload_id=file_id, user_id=current_user.id)
