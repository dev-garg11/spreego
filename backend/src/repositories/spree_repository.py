from typing import List, Optional
from sqlalchemy.orm import Session, contains_eager, joinedload
from src.models.spree import Spree, SpreeType, SpreeVisibility
from src.models.follow import Follow
from src.models.user import User
from src.repositories.base_repository import BaseRepository


class SpreeRepository(BaseRepository[Spree]):
    def __init__(self, db: Session):
        super().__init__(Spree, db)

    def get_by_id(self, id: str) -> Optional[Spree]:
        return (
            self.db.query(Spree)
            .options(joinedload(Spree.creator))
            .filter(Spree.id == id)
            .first()
        )

    def get_public_sprees(
        self,
        spree_type: Optional[SpreeType] = None,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
        tab: str = "for_you",
        requesting_user_id: Optional[str] = None,
        creator_id: Optional[str] = None,
    ) -> List[Spree]:
        query = (
            self.db.query(Spree)
            .join(Spree.creator)
            .options(contains_eager(Spree.creator))
            .filter(
                Spree.visibility == SpreeVisibility.PUBLIC,
                User.is_active.is_(True),
            )
        )
        if spree_type is not None:
            query = query.filter(Spree.type == spree_type)
        if creator_id:
            query = query.filter(Spree.creator_id == creator_id.strip())
        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.filter(
                (Spree.title.ilike(term)) | (Spree.description.ilike(term))
            )
        if tab.strip().lower() == "following":
            if not requesting_user_id:
                return []
            followed_creators = (
                self.db.query(Follow.following_id)
                .filter(Follow.follower_id == requesting_user_id)
                .scalar_subquery()
            )
            query = query.filter(Spree.creator_id.in_(followed_creators))
        return query.order_by(Spree.created_at.desc(), Spree.id.desc()).offset(skip).limit(limit).all()

    def count_public_sprees(self, spree_type: Optional[SpreeType] = None) -> int:
        query = (
            self.db.query(Spree)
            .join(Spree.creator)
            .filter(
                Spree.visibility == SpreeVisibility.PUBLIC,
                User.is_active.is_(True),
            )
        )
        if spree_type is not None:
            query = query.filter(Spree.type == spree_type)
        return query.count()
