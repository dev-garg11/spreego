from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from src.models.open import OpenStatus, OpenType
from src.models.user import User
from src.services.open_service import OpenService
from src.validations.feed_schemas import FeedSpreeResponse
from src.validations.open_schemas import (
    CreateOpenRequest,
    JoinOpenResponse,
    OpenRankingItem,
    OpenResponse,
    OpenSubmissionResponse,
    SubmitSpreeRequest,
)


class OpenController:
    @staticmethod
    def create_open(
        current_user: User,
        payload: CreateOpenRequest,
        db: Session,
    ) -> OpenResponse:
        service = OpenService(db)
        try:
            open_obj = service.create_open(creator_id=current_user.id, payload=payload)
            return OpenResponse.model_validate(open_obj)
        except PermissionError as err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))
        except (ValueError, IntegrityError) as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def list_opens(
        open_type: Optional[OpenType],
        open_status: Optional[OpenStatus],
        skip: int,
        limit: int,
        db: Session,
    ) -> List[OpenResponse]:
        service = OpenService(db)
        opens = service.list_opens(
            open_type=open_type,
            open_status=open_status,
            skip=skip,
            limit=limit,
        )
        return [OpenResponse.model_validate(o) for o in opens]

    @staticmethod
    def get_open(open_id: str, db: Session) -> OpenResponse:
        service = OpenService(db)
        try:
            open_obj = service.get_open(open_id)
            return OpenResponse.model_validate(open_obj)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))

    @staticmethod
    def join_open(open_id: str, current_user: User, db: Session) -> JoinOpenResponse:
        service = OpenService(db)
        try:
            participant = service.join_open(open_id=open_id, current_user=current_user)
            return JoinOpenResponse(
                open_id=open_id,
                user_id=current_user.id,
                joined_at=participant.joined_at,
            )
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except PermissionError as err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))
        except (ValueError, IntegrityError) as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def submit_spree(
        open_id: str,
        payload: SubmitSpreeRequest,
        current_user: User,
        db: Session,
    ) -> OpenSubmissionResponse:
        service = OpenService(db)
        try:
            submission = service.submit_spree(
                open_id=open_id,
                spree_id=payload.spree_id,
                current_user=current_user,
            )
            return OpenSubmissionResponse.model_validate(submission)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except PermissionError as err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))
        except (ValueError, IntegrityError) as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def get_feed(
        open_id: str,
        skip: int,
        limit: int,
        db: Session,
    ) -> List[FeedSpreeResponse]:
        service = OpenService(db)
        try:
            return service.get_feed(open_id=open_id, skip=skip, limit=limit)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))

    @staticmethod
    def get_ranking(open_id: str, db: Session) -> List[OpenRankingItem]:
        service = OpenService(db)
        try:
            return service.get_ranking(open_id=open_id)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
