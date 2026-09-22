from typing import Optional
from sqlalchemy.orm import Session
from src.models.profile import Profile
from src.repositories.base_repository import BaseRepository


class ProfileRepository(BaseRepository[Profile]):
    def __init__(self, db: Session):
        super().__init__(Profile, db)

    def get_by_user_id(self, user_id: str) -> Optional[Profile]:
        return self.db.query(Profile).filter(Profile.user_id == user_id).first()

    def get_by_username(self, username: str) -> Optional[Profile]:
        return self.db.query(Profile).filter(Profile.username == username).first()
