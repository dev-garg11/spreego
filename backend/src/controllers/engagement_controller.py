from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from src.models.user import User
from src.services.engagement_service import EngagementService
from src.validations.engagement_schemas import (
    ClapResponse,
    CommentResponse,
    CreateCommentRequest,
    RecordShareRequest,
    RecordViewRequest,
    SaveResponse,
    ShareResponse,
    UnclapResponse,
    UnsaveResponse,
    ViewResponse,
)


class EngagementController:
    @staticmethod
    def record_view(
        spree_id: str,
        user: Optional[User],
        payload: Optional[RecordViewRequest],
        db: Session,
    ) -> ViewResponse:
        service = EngagementService(db)
        try:
            view = service.record_view(
                spree_id=spree_id,
                user_id=user.id if user else None,
                payload=payload,
            )
            return ViewResponse(
                id=view.id,
                spree_id=view.spree_id,
                user_id=view.user_id,
                watch_duration=view.watch_duration,
                completed=view.completed,
                created_at=view.created_at,
            )
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def clap_spree(
        spree_id: str,
        current_user: User,
        db: Session,
    ) -> ClapResponse:
        service = EngagementService(db)
        try:
            service.clap_spree(spree_id=spree_id, user_id=current_user.id)
            return ClapResponse(message="Spree clapped successfully.", clapped=True)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def unclap_spree(
        spree_id: str,
        current_user: User,
        db: Session,
    ) -> UnclapResponse:
        service = EngagementService(db)
        try:
            service.unclap_spree(spree_id=spree_id, user_id=current_user.id)
            return UnclapResponse(message="Clap removed successfully.", clapped=False)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def create_comment(
        spree_id: str,
        current_user: User,
        payload: CreateCommentRequest,
        db: Session,
    ) -> CommentResponse:
        service = EngagementService(db)
        try:
            return service.create_comment(
                spree_id=spree_id,
                user_id=current_user.id,
                payload=payload,
            )
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def get_comments(
        spree_id: str,
        skip: int,
        limit: int,
        db: Session,
    ) -> List[CommentResponse]:
        service = EngagementService(db)
        try:
            return service.get_comments(spree_id=spree_id, skip=skip, limit=limit)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def record_share(
        spree_id: str,
        user: Optional[User],
        payload: Optional[RecordShareRequest],
        db: Session,
    ) -> ShareResponse:
        service = EngagementService(db)
        try:
            share, share_count = service.record_share(
                spree_id=spree_id,
                user_id=user.id if user else None,
                payload=payload,
            )
            return ShareResponse(
                message="Spree shared successfully.",
                id=share.id,
                spree_id=share.spree_id,
                user_id=share.user_id,
                platform=share.platform,
                share_count=share_count,
                created_at=share.created_at,
            )
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def save_spree(
        spree_id: str,
        current_user: User,
        db: Session,
    ) -> SaveResponse:
        service = EngagementService(db)
        try:
            service.save_spree(spree_id=spree_id, user_id=current_user.id)
            return SaveResponse(message="Spree saved successfully.", saved=True)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def unsave_spree(
        spree_id: str,
        current_user: User,
        db: Session,
    ) -> UnsaveResponse:
        service = EngagementService(db)
        try:
            service.unsave_spree(spree_id=spree_id, user_id=current_user.id)
            return UnsaveResponse(message="Spree unsaved successfully.", saved=False)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
