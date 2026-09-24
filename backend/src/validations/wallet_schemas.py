from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import Field, field_validator
from src.models.wallet import (
    PayoutStatus,
    TransactionType,
    WalletStatus,
    WalletTransactionType,
)
from src.validations.auth_schemas import BaseSchema


class PayoutRequest(BaseSchema):
    amount: float = Field(..., description="Payout withdrawal amount (> 0)")
    payout_method: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {"upi_id": "creator@upi"},
        description="Destination payout details (UPI or bank account)",
    )
    description: Optional[str] = Field(None, max_length=500, description="Optional withdrawal reference/note")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        import math
        if isinstance(v, bool):
            raise ValueError("Amount must be a numeric value, not a boolean.")
        if math.isnan(v) or math.isinf(v):
            raise ValueError("Amount must be a valid finite number.")
        rounded = round(float(v), 2)
        if rounded <= 0.0:
            raise ValueError("Payout amount must be greater than zero.")
        return rounded

    @field_validator("payout_method")
    @classmethod
    def validate_payout_method(cls, v: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not v:
            return {"upi_id": "creator@upi"}
        return v


class WalletResponse(BaseSchema):
    id: str
    user_id: str
    currency: str = "INR"
    status: WalletStatus = WalletStatus.ACTIVE
    is_active: bool = True
    available_balance: float = 0.0
    balance: float = 0.0
    pending_payout_balance: float = 0.0
    created_at: datetime
    updated_at: datetime


class WalletTransactionResponse(BaseSchema):
    id: str
    wallet_id: str
    type: WalletTransactionType
    amount: float
    reference_id: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime


class PayoutResponse(BaseSchema):
    id: str
    wallet_id: str
    user_id: str
    amount: float
    status: PayoutStatus = PayoutStatus.PENDING
    payout_method: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
