from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session, contains_eager
from src.models.follow import Follow
from src.models.profile import Profile
from src.models.user import User
from src.repositories.base_repository import BaseRepository


class FollowRepository(BaseRepository[Follow]):
    def __init__(self, db: Session):
        super().__init__(Follow, db)

    def get_follow(self, follower_id: str, following_id: str) -> Optional[Follow]:
        return (
            self.db.query(Follow)
            .filter(
                Follow.follower_id == follower_id,
                Follow.following_id == following_id,
            )
            .first()
        )

    def count_followers(self, user_id: str) -> int:
        return (
            self.db.query(func.count(Follow.id))
            .join(Follow.follower)
            .filter(Follow.following_id == user_id, User.is_active.is_(True))
            .scalar()
            or 0
        )

    def count_following(self, user_id: str) -> int:
        return (
            self.db.query(func.count(Follow.id))
            .join(Follow.following)
            .filter(Follow.follower_id == user_id, User.is_active.is_(True))
            .scalar()
            or 0
        )

    def get_followers(self, user_id: str, skip: int = 0, limit: int = 20) -> List[Follow]:
        return (
            self.db.query(Follow)
            .join(Follow.follower)
            .outerjoin(User.profile)
            .options(contains_eager(Follow.follower).contains_eager(User.profile))
            .filter(Follow.following_id == user_id, User.is_active.is_(True))
            .order_by(Follow.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_following(self, user_id: str, skip: int = 0, limit: int = 20) -> List[Follow]:
        return (
            self.db.query(Follow)
            .join(Follow.following)
            .outerjoin(User.profile)
            .options(contains_eager(Follow.following).contains_eager(User.profile))
            .filter(Follow.follower_id == user_id, User.is_active.is_(True))
            .order_by(Follow.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
