from typing import Optional
from fastapi import APIRouter, Body, Depends, status
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.buzzer_controller import BuzzerController
from src.middlewares.auth_middleware import get_current_user, get_optional_current_user
from src.models.user import User
from src.validations.buzzer_schemas import (
    BuzzerCampaignResponse,
    CreateBuzzerRequest,
)

router = APIRouter(prefix="/api/v1/sprees", tags=["Buzzer"])


@router.post(
    "/{id}/buzzer",
    response_model=BuzzerCampaignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Activate 24-hour Buzzer boost on a Spree",
)
@router.post(
    "/{id}/buzzer/",
    response_model=BuzzerCampaignResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def activate_buzzer(
    id: str,
    payload: Optional[CreateBuzzerRequest] = Body(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BuzzerCampaignResponse:
    """Authenticated endpoint for creators to activate a 24-hour Buzzer boost on their Spree."""
    return BuzzerController.activate_buzzer(
        spree_id=id,
        current_user=current_user,
        payload=payload,
        db=db,
    )


@router.get(
    "/{id}/buzzer",
    response_model=BuzzerCampaignResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Buzzer status and campaign info for a Spree",
)
@router.get(
    "/{id}/buzzer/",
    response_model=BuzzerCampaignResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_buzzer(
    id: str,
    requesting_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> BuzzerCampaignResponse:
    """Get Buzzer status and campaign info for a Spree."""
    return BuzzerController.get_buzzer(spree_id=id, requesting_user=requesting_user, db=db)
