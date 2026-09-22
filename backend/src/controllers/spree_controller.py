from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from src.models.spree import SpreeType
from src.models.user import User
from src.services.spree_service import AuthenticationRequiredError, SpreeService
from src.validations.auth_schemas import MessageResponse
from src.validations.spree_schemas import (
    CreateSpreeRequest,
    SpreeResponse,
    UpdateSpreeRequest,
)


class SpreeController:
    @staticmethod
    def create_spree(
        current_user: User,
        payload: CreateSpreeRequest,
        db: Session,
    ) -> SpreeResponse:
        service = SpreeService(db)
        try:
            spree = service.create_spree(creator_id=current_user.id, payload=payload)
            return SpreeResponse.model_validate(spree)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except (ValueError, IntegrityError) as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def get_spree(
        spree_id: str,
        requesting_user: Optional[User],
        db: Session,
    ) -> SpreeResponse:
        service = SpreeService(db)
        try:
            spree = service.get_spree(spree_id=spree_id, requesting_user=requesting_user)
            return SpreeResponse.model_validate(spree)
        except AuthenticationRequiredError as err:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(err),
                headers={"WWW-Authenticate": "Bearer"},
            )
        except PermissionError as err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))

    @staticmethod
    def update_spree(
        spree_id: str,
        current_user: User,
        payload: UpdateSpreeRequest,
        db: Session,
    ) -> SpreeResponse:
        service = SpreeService(db)
        try:
            spree = service.update_spree(
                spree_id=spree_id,
                current_user=current_user,
                payload=payload,
            )
            return SpreeResponse.model_validate(spree)
        except PermissionError as err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except (ValueError, IntegrityError) as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def delete_spree(
        spree_id: str,
        current_user: User,
        db: Session,
    ) -> MessageResponse:
        service = SpreeService(db)
        try:
            service.delete_spree(spree_id=spree_id, current_user=current_user)
            return MessageResponse(message="Spree deleted successfully.")
        except PermissionError as err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except (ValueError, IntegrityError) as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def list_public_sprees(
        spree_type: Optional[SpreeType],
        skip: int,
        limit: int,
        db: Session,
    ) -> List[SpreeResponse]:
        service = SpreeService(db)
        sprees = service.list_public_sprees(spree_type=spree_type, skip=skip, limit=limit)
        return [SpreeResponse.model_validate(s) for s in sprees]
