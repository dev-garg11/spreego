from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional
from pydantic import Field, field_validator
from src.models.membership import MembershipTierType, SubscriptionStatus
from src.validations.auth_schemas import BaseSchema


class PlanCreatorInfo(BaseSchema):
    id: str
    username: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None

    @classmethod
    def from_user(cls, user: Any) -> Optional["PlanCreatorInfo"]:
        if not user:
            return None
        prof = getattr(user, "profile", None)
        return cls(
            id=str(user.id),
            username=getattr(prof, "username", None) if prof else None,
            full_name=getattr(prof, "full_name", None) if prof else None,
            avatar_url=getattr(prof, "avatar_url", None) if prof else None,
        )


class CreateMembershipPlanRequest(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255, description="Membership plan name")
    description: Optional[str] = Field(None, max_length=5000, description="Plan description")
    monthly_price: Optional[float] = Field(default=0.0, ge=0.0, description="Monthly price (default 0.0)")
    currency: Optional[str] = Field(default="INR", max_length=10, description="Currency code (e.g. INR)")
    tier_type: Optional[MembershipTierType] = Field(
        default=MembershipTierType.FREE, description="FREE or VIP tier"
    )
    benefits: Optional[List[str]] = Field(default_factory=list, description="List of perks / benefits")
    is_active: Optional[bool] = Field(default=True, description="Whether plan is active")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Plan name cannot be empty.")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: Optional[str]) -> str:
        if v is not None and v.strip():
            return v.strip().upper()
        return "INR"

    @field_validator("benefits")
    @classmethod
    def validate_benefits(cls, v: Optional[List[str]]) -> List[str]:
        if v is None:
            return []
        cleaned = [str(item).strip() for item in v if str(item).strip()]
        return cleaned


class UpdateMembershipPlanRequest(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    monthly_price: Optional[float] = Field(None, ge=0.0)
    currency: Optional[str] = Field(None, max_length=10)
    tier_type: Optional[MembershipTierType] = None
    benefits: Optional[List[str]] = None
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Plan name cannot be empty.")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip().upper()
            if not clean:
                raise ValueError("Currency cannot be empty.")
            return clean
        return v

    @field_validator("benefits")
    @classmethod
    def validate_benefits(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        return [str(item).strip() for item in v if str(item).strip()]


class SubscribeMembershipRequest(BaseSchema):
    plan_id: str = Field(..., description="ID of the membership plan to subscribe to")

    @field_validator("plan_id")
    @classmethod
    def validate_plan_id(cls, v: str) -> str:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("plan_id cannot be empty.")
        return v


class MembershipPlanResponse(BaseSchema):
    id: str
    creator_id: str
    name: str
    description: Optional[str] = None
    monthly_price: float = 0.0
    currency: str = "INR"
    tier_type: MembershipTierType = MembershipTierType.FREE
    benefits: List[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    creator: Optional[PlanCreatorInfo] = None
    subscribers_count: Optional[int] = 0

    @field_validator("benefits", mode="before")
    @classmethod
    def parse_benefits(cls, v: Any) -> List[str]:
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x) for x in v]
        return []

    @classmethod
    def from_orm_model(cls, plan: Any) -> "MembershipPlanResponse":
        creator_info = PlanCreatorInfo.from_user(getattr(plan, "creator", None))
        raw_benefits = getattr(plan, "benefits", [])
        benefits = list(raw_benefits) if isinstance(raw_benefits, list) else []
        sub_count = getattr(plan, "subscribers_count", 0)
        c_at = getattr(plan, "created_at", None) or datetime.now(timezone.utc)
        u_at = getattr(plan, "updated_at", None) or datetime.now(timezone.utc)
        return cls(
            id=str(plan.id),
            creator_id=str(plan.creator_id),
            name=str(plan.name),
            description=plan.description,
            monthly_price=float(plan.monthly_price or 0.0),
            currency=str(plan.currency or "INR"),
            tier_type=plan.tier_type,
            benefits=benefits,
            is_active=bool(plan.is_active),
            created_at=c_at,
            updated_at=u_at,
            creator=creator_info,
            subscribers_count=sub_count,
        )


class SubscriptionResponse(BaseSchema):
    id: str
    plan_id: str
    user_id: str
    status: SubscriptionStatus
    current_period_start: datetime
    current_period_end: datetime
    created_at: datetime
    updated_at: datetime
    plan: Optional[MembershipPlanResponse] = None

    @classmethod
    def from_orm_model(cls, sub: Any) -> "SubscriptionResponse":
        plan_obj = getattr(sub, "plan", None)
        plan_resp = MembershipPlanResponse.from_orm_model(plan_obj) if plan_obj else None
        p_start = getattr(sub, "current_period_start", None) or datetime.now(timezone.utc)
        p_end = getattr(sub, "current_period_end", None) or (datetime.now(timezone.utc) + timedelta(days=30))
        c_at = getattr(sub, "created_at", None) or datetime.now(timezone.utc)
        u_at = getattr(sub, "updated_at", None) or datetime.now(timezone.utc)
        return cls(
            id=str(sub.id),
            plan_id=str(sub.plan_id),
            user_id=str(sub.user_id),
            status=sub.status,
            current_period_start=p_start,
            current_period_end=p_end,
            created_at=c_at,
            updated_at=u_at,
            plan=plan_resp,
        )
