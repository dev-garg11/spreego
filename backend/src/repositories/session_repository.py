from typing import Optional
from sqlalchemy.orm import Session
from src.models.user_session import UserSession
from src.repositories.base_repository import BaseRepository


class SessionRepository(BaseRepository[UserSession]):
    def __init__(self, db: Session):
        super().__init__(UserSession, db)

    def get_by_refresh_token(self, refresh_token: str) -> Optional[UserSession]:
        if not refresh_token or not refresh_token.strip():
            return None
        return (
            self.db.query(UserSession)
            .filter(UserSession.refresh_token == refresh_token.strip())
            .first()
        )

    def revoke_by_token(self, refresh_token: str, user_id: Optional[str] = None) -> bool:
        if not refresh_token or not refresh_token.strip():
            return False
        clean_token = refresh_token.strip()
        try:
            query = self.db.query(UserSession).filter(UserSession.refresh_token == clean_token)
            if user_id is not None:
                query = query.filter(UserSession.user_id == user_id)
            session = query.first()
            if session:
                session.is_revoked = True
                self.db.commit()
                return True
            return False
        except Exception:
            self.db.rollback()
            raise

    def revoke_all_for_user(self, user_id: str) -> int:
        try:
            updated_count = (
                self.db.query(UserSession)
                .filter(UserSession.user_id == user_id, UserSession.is_revoked.is_(False))
                .update({"is_revoked": True}, synchronize_session="fetch")
            )
            self.db.commit()
            return updated_count
        except Exception:
            self.db.rollback()
            raise
