from typing import List, Optional
from sqlalchemy.orm import Session, contains_eager, joinedload
from src.models.spree import Spree, SpreeType, SpreeVisibility
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
