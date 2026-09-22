import math
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from src.models.buzzer import BuzzerCampaign, BuzzerStatus
from src.models.spree import SpreeVisibility
from src.models.user import User
from src.repositories.buzzer_repository import BuzzerRepository
from src.repositories.follow_repository import FollowRepository
from src.repositories.spree_repository import SpreeRepository
from src.services.spree_service import AuthenticationRequiredError


class BuzzerService:
    def __init__(self, db: Session):
        self.db = db
        self.buzzer_repo = BuzzerRepository(db)
        self.spree_repo = SpreeRepository(db)
        self.follow_repo = FollowRepository(db)

    def activate_buzzer(
        self,
        spree_id: str,
        current_user: User,
        boost_multiplier: Optional[float] = None,
    ) -> BuzzerCampaign:
        if not current_user or not current_user.is_active:
            raise PermissionError("User account is deactivated.")

        spree = self.spree_repo.get_by_id(spree_id)
        if not spree or not spree.creator or not spree.creator.is_active:
            raise LookupError("Spree not found.")

        # Strictly enforce creator ownership
        if spree.creator_id != current_user.id:
            raise PermissionError("Only the creator can activate Buzzer on their Spree.")

        multiplier = 1.5 if boost_multiplier is None else float(boost_multiplier)
        if not (1.0 <= multiplier <= 5.0) or math.isnan(multiplier) or math.isinf(multiplier):
            raise ValueError("Boost multiplier must be between 1.0 and 5.0.")

        now = datetime.now(timezone.utc)

        # Transition any naturally expired campaigns to EXPIRED status
        self.buzzer_repo.expire_outdated_campaigns(spree_id=spree_id, now=now)

        # Check for existing active campaign
        existing = self.buzzer_repo.get_active_campaign(spree_id=spree_id, now=now)
        if existing:
            raise ValueError("An active Buzzer campaign already exists for this Spree.")

        campaign = BuzzerCampaign(
            spree_id=spree.id,
            creator_id=current_user.id,
            start_at=now,
            end_at=now + timedelta(hours=24),
            status=BuzzerStatus.ACTIVE,
            boost_multiplier=multiplier,
            created_at=now,
        )
        try:
            return self.buzzer_repo.create(campaign)
        except IntegrityError:
            self.db.rollback()
            raise ValueError("An active Buzzer campaign already exists for this Spree.")

    def get_buzzer(
        self,
        spree_id: str,
        requesting_user: Optional[User] = None,
    ) -> BuzzerCampaign:
        if requesting_user is not None and not requesting_user.is_active:
            raise PermissionError("User account is deactivated.")

        spree = self.spree_repo.get_by_id(spree_id)
        if not spree or not spree.creator or not spree.creator.is_active:
            raise LookupError("Spree not found.")

        # Visibility checks matching SpreeService.get_spree
        if spree.visibility == SpreeVisibility.PRIVATE:
            if requesting_user is None:
                raise AuthenticationRequiredError("Authentication required to view this private spree.")
            if requesting_user.id != spree.creator_id:
                raise PermissionError("You do not have permission to view this private spree.")
        elif spree.visibility == SpreeVisibility.FOLLOWERS_ONLY:
            if requesting_user is None:
                raise AuthenticationRequiredError("Authentication required to view this spree.")
            if requesting_user.id != spree.creator_id:
                follow = self.follow_repo.get_follow(
                    follower_id=requesting_user.id,
                    following_id=spree.creator_id,
                )
                if not follow:
                    raise PermissionError("You must follow the creator to view this spree.")

        now = datetime.now(timezone.utc)

        # Transition any naturally expired campaigns to EXPIRED status
        self.buzzer_repo.expire_outdated_campaigns(spree_id=spree_id, now=now)

        # Check for active first, otherwise latest campaign
        campaign = self.buzzer_repo.get_active_campaign(spree_id=spree_id, now=now)
        if not campaign:
            campaign = self.buzzer_repo.get_latest_campaign(spree_id=spree_id)

        if not campaign:
            raise LookupError("Buzzer campaign not found for this Spree.")

        return campaign

    def cancel_buzzer(self, spree_id: str, current_user: User) -> BuzzerCampaign:
        if not current_user or not current_user.is_active:
            raise PermissionError("User account is deactivated.")

        spree = self.spree_repo.get_by_id(spree_id)
        if not spree or not spree.creator or not spree.creator.is_active:
            raise LookupError("Spree not found.")
        if spree.creator_id != current_user.id:
            raise PermissionError("Only the creator can cancel Buzzer on their Spree.")
        now = datetime.now(timezone.utc)
        campaign = self.buzzer_repo.get_active_campaign(spree_id=spree_id, now=now)
        if not campaign:
            raise LookupError("No active Buzzer campaign found to cancel.")
        campaign.status = BuzzerStatus.CANCELLED
        return self.buzzer_repo.update(campaign)
