from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from src.models.user import User
from src.services.moderation_service import ModerationService
from src.validations.auth_schemas import MessageResponse
from src.validations.moderation_schemas import (
    BlockedUserItem,
    BlockResponse,
    CreateReportRequest,
    MutedUserItem,
    MuteResponse,
    ReportResponse,
)


class ModerationController:
    @staticmethod
    def create_report(
        current_user: User,
        payload: CreateReportRequest,
        db: Session,
    ) -> ReportResponse:
        service = ModerationService(db)
        try:
            report = service.create_report(current_user=current_user, payload=payload)
            return ReportResponse.model_validate(report)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def block_user(
        target_user_id: str,
        current_user: User,
        db: Session,
    ) -> BlockResponse:
        service = ModerationService(db)
        try:
            return service.block_user(current_user=current_user, target_user_id=target_user_id)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def unblock_user(
        target_user_id: str,
        current_user: User,
        db: Session,
    ) -> MessageResponse:
        service = ModerationService(db)
        try:
            return service.unblock_user(current_user=current_user, target_user_id=target_user_id)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def get_blocked_users(
        current_user: User,
        skip: int,
        limit: int,
        db: Session,
    ) -> List[BlockedUserItem]:
        service = ModerationService(db)
        return service.get_blocked_users(current_user=current_user, skip=skip, limit=limit)

    @staticmethod
    def mute_user(
        target_user_id: str,
        current_user: User,
        db: Session,
    ) -> MuteResponse:
        service = ModerationService(db)
        try:
            return service.mute_user(current_user=current_user, target_user_id=target_user_id)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def unmute_user(
        target_user_id: str,
        current_user: User,
        db: Session,
    ) -> MessageResponse:
        service = ModerationService(db)
        try:
            return service.unmute_user(current_user=current_user, target_user_id=target_user_id)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def get_muted_users(
        current_user: User,
        skip: int,
        limit: int,
        db: Session,
    ) -> List[MutedUserItem]:
        service = ModerationService(db)
        return service.get_muted_users(current_user=current_user, skip=skip, limit=limit)
