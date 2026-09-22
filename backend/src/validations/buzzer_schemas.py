from datetime import datetime
from typing import Optional
from pydantic import Field
from src.models.buzzer import BuzzerStatus
from src.validations.auth_schemas import BaseSchema


class CreateBuzzerRequest(BaseSchema):
    boost_multiplier: Optional[float] = Field(
        default=1.5,
        ge=1.0,
        le=5.0,
        description="Ranking boost multiplier (1.0 to 5.0, default 1.5)",
    )


class BuzzerCampaignResponse(BaseSchema):
    id: str
    spree_id: str
    creator_id: str
    start_at: datetime
    end_at: datetime
    status: BuzzerStatus
    boost_multiplier: float = 1.5
    is_active: bool = True
    created_at: datetime
