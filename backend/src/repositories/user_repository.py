from typing import Optional
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload
from src.models.user import User
from src.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_id(self, user_id: str) -> Optional[User]:
        return (
            self.db.query(User)
            .options(joinedload(User.profile))
            .filter(User.id == user_id)
            .first()
        )

    def get_by_phone(self, phone_number: str) -> Optional[User]:
        clean = phone_number.strip() if phone_number else ""
        return (
            self.db.query(User)
            .options(joinedload(User.profile))
            .filter(User.phone_number == clean)
            .first()
        )

    def get_by_email(self, email: str) -> Optional[User]:
        clean = email.strip().lower() if email else ""
        return (
            self.db.query(User)
            .options(joinedload(User.profile))
            .filter(User.email == clean)
            .first()
        )

    def get_by_identifier(self, identifier: str) -> Optional[User]:
        clean = identifier.strip() if identifier else ""
        if "@" in clean:
            clean = clean.lower()
        return (
            self.db.query(User)
            .options(joinedload(User.profile))
            .filter(or_(User.phone_number == clean, User.email == clean))
            .first()
        )
