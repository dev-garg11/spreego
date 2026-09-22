from typing import List, Optional
from sqlalchemy.orm import Session
from src.models.spree import SpreeType
from src.models.user import User
from src.services.feed_ranking_service import FeedRankingService
from src.validations.feed_schemas import FeedSpreeResponse


class FeedController:
    @staticmethod
    def get_feed(
        requesting_user: Optional[User],
        spree_type: Optional[SpreeType],
        skip: int,
        limit: int,
        db: Session,
    ) -> List[FeedSpreeResponse]:
        service = FeedRankingService(db)
        return service.get_ranked_feed(
            requesting_user=requesting_user,
            spree_type=spree_type,
            skip=skip,
            limit=limit,
        )
