from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from src.models.user import User
from src.services.buzzer_service import BuzzerService
from src.services.spree_service import AuthenticationRequiredError
from src.validations.buzzer_schemas import (
    BuzzerCampaignResponse,
    CreateBuzzerRequest,
)


class BuzzerController:
    @staticmethod
    def activate_buzzer(
        spree_id: str,
        current_user: User,
        payload: Optional[CreateBuzzerRequest],
        db: Session,
    ) -> BuzzerCampaignResponse:
        service = BuzzerService(db)
        try:
            multiplier = payload.boost_multiplier if payload else None
            campaign = service.activate_buzzer(
                spree_id=spree_id,
                current_user=current_user,
                boost_multiplier=multiplier,
            )
            return BuzzerCampaignResponse.model_validate(campaign)
        except PermissionError as err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def get_buzzer(
        spree_id: str,
        requesting_user: Optional[User],
        db: Session,
    ) -> BuzzerCampaignResponse:
        service = BuzzerService(db)
        try:
            campaign = service.get_buzzer(spree_id=spree_id, requesting_user=requesting_user)
            return BuzzerCampaignResponse.model_validate(campaign)
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
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
