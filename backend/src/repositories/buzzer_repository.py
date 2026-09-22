from datetime import datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from src.models.buzzer import BuzzerCampaign, BuzzerStatus
from src.repositories.base_repository import BaseRepository


def ensure_utc(dt: Optional[datetime] = None) -> datetime:
    """Normalize datetime to UTC timezone-aware datetime."""
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class BuzzerRepository(BaseRepository[BuzzerCampaign]):
    def __init__(self, db: Session):
        super().__init__(BuzzerCampaign, db)

    def get_by_id(self, id: str) -> Optional[BuzzerCampaign]:
        return self.db.query(BuzzerCampaign).filter(BuzzerCampaign.id == id).first()

    def expire_outdated_campaigns(
        self,
        spree_id: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> int:
        """Expire all ACTIVE campaigns whose end_at has passed."""
        current_time = ensure_utc(now)
        query = self.db.query(BuzzerCampaign).filter(
            BuzzerCampaign.status == BuzzerStatus.ACTIVE,
            BuzzerCampaign.end_at < current_time,
        )
        if spree_id:
            query = query.filter(BuzzerCampaign.spree_id == spree_id)
        outdated = query.all()
        if not outdated:
            return 0
        for c in outdated:
            c.status = BuzzerStatus.EXPIRED
        self.db.commit()
        return len(outdated)

    def get_active_campaign(
        self,
        spree_id: str,
        now: Optional[datetime] = None,
    ) -> Optional[BuzzerCampaign]:
        current_time = ensure_utc(now)
        return (
            self.db.query(BuzzerCampaign)
            .filter(
                BuzzerCampaign.spree_id == spree_id,
                BuzzerCampaign.status == BuzzerStatus.ACTIVE,
                BuzzerCampaign.start_at <= current_time,
                BuzzerCampaign.end_at >= current_time,
            )
            .order_by(BuzzerCampaign.created_at.desc())
            .first()
        )

    def get_latest_campaign(self, spree_id: str) -> Optional[BuzzerCampaign]:
        return (
            self.db.query(BuzzerCampaign)
            .filter(BuzzerCampaign.spree_id == spree_id)
            .order_by(BuzzerCampaign.created_at.desc(), BuzzerCampaign.id.desc())
            .first()
        )

    def cancel_campaign(self, campaign_id: str) -> Optional[BuzzerCampaign]:
        campaign = self.get_by_id(campaign_id)
        if campaign and campaign.status == BuzzerStatus.ACTIVE:
            campaign.status = BuzzerStatus.CANCELLED
            return self.update(campaign)
        return campaign

    def get_active_campaigns_for_sprees(
        self,
        spree_ids: List[str],
        now: Optional[datetime] = None,
    ) -> Dict[str, BuzzerCampaign]:
        if not spree_ids:
            return {}
        current_time = ensure_utc(now)
        result: Dict[str, BuzzerCampaign] = {}
        # Batch in chunks of 500 to guarantee database parameter safety
        for i in range(0, len(spree_ids), 500):
            chunk = spree_ids[i : i + 500]
            campaigns = (
                self.db.query(BuzzerCampaign)
                .filter(
                    BuzzerCampaign.spree_id.in_(chunk),
                    BuzzerCampaign.status == BuzzerStatus.ACTIVE,
                    BuzzerCampaign.start_at <= current_time,
                    BuzzerCampaign.end_at >= current_time,
                )
                .order_by(BuzzerCampaign.created_at.desc())
                .all()
            )
            # One active campaign per spree (latest wins in case of multiple)
            for c in campaigns:
                if c.spree_id not in result:
                    result[c.spree_id] = c
        return result
