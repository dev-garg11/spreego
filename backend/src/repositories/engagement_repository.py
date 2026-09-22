from typing import List, Optional
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from src.models.engagement import (
    SpreeClap,
    SpreeComment,
    SpreeSave,
    SpreeShare,
    SpreeView,
)
from src.models.spree import Spree
from src.models.user import User


class EngagementRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_spree(self, spree_id: str) -> Optional[Spree]:
        return self.db.query(Spree).filter(Spree.id == spree_id).first()

    def record_view(
        self,
        spree_id: str,
        user_id: Optional[str],
        watch_duration: float,
        completed: bool,
    ) -> SpreeView:
        view = SpreeView(
            spree_id=spree_id,
            user_id=user_id,
            watch_duration=watch_duration,
            completed=completed,
        )
        try:
            self.db.add(view)
            self.db.commit()
            self.db.refresh(view)
            return view
        except Exception:
            self.db.rollback()
            raise

    def get_clap(self, spree_id: str, user_id: str) -> Optional[SpreeClap]:
        return (
            self.db.query(SpreeClap)
            .filter(SpreeClap.spree_id == spree_id, SpreeClap.user_id == user_id)
            .first()
        )

    def add_clap(self, spree_id: str, user_id: str) -> SpreeClap:
        existing = self.get_clap(spree_id=spree_id, user_id=user_id)
        if existing:
            return existing

        clap = SpreeClap(spree_id=spree_id, user_id=user_id)
        try:
            self.db.add(clap)
            self.db.commit()
            self.db.refresh(clap)
            return clap
        except IntegrityError:
            self.db.rollback()
            found = self.get_clap(spree_id=spree_id, user_id=user_id)
            if found:
                return found
            raise
        except Exception:
            self.db.rollback()
            raise

    def remove_clap(self, spree_id: str, user_id: str) -> bool:
        clap = self.get_clap(spree_id=spree_id, user_id=user_id)
        if not clap:
            return False
        try:
            self.db.delete(clap)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise

    def create_comment(
        self,
        spree_id: str,
        user_id: str,
        text: str,
        parent_id: Optional[str] = None,
    ) -> SpreeComment:
        comment = SpreeComment(
            spree_id=spree_id,
            user_id=user_id,
            text=text,
            parent_id=parent_id,
        )
        try:
            self.db.add(comment)
            self.db.commit()
            self.db.refresh(comment)
            return comment
        except Exception:
            self.db.rollback()
            raise

    def get_comment_by_id(self, comment_id: str) -> Optional[SpreeComment]:
        return (
            self.db.query(SpreeComment)
            .options(joinedload(SpreeComment.user).joinedload(User.profile))
            .filter(SpreeComment.id == comment_id)
            .first()
        )

    def get_comments(
        self,
        spree_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> List[SpreeComment]:
        return (
            self.db.query(SpreeComment)
            .options(joinedload(SpreeComment.user).joinedload(User.profile))
            .filter(SpreeComment.spree_id == spree_id)
            .order_by(SpreeComment.created_at.asc(), SpreeComment.id.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_comments(self, spree_id: str) -> int:
        return self.db.query(SpreeComment).filter(SpreeComment.spree_id == spree_id).count()

    def record_share(
        self,
        spree_id: str,
        user_id: Optional[str],
        platform: Optional[str] = None,
    ) -> SpreeShare:
        share = SpreeShare(
            spree_id=spree_id,
            user_id=user_id,
            platform=platform,
        )
        try:
            self.db.add(share)
            self.db.commit()
            self.db.refresh(share)
            return share
        except Exception:
            self.db.rollback()
            raise

    def count_shares(self, spree_id: str) -> int:
        return self.db.query(SpreeShare).filter(SpreeShare.spree_id == spree_id).count()

    def get_save(self, spree_id: str, user_id: str) -> Optional[SpreeSave]:
        return (
            self.db.query(SpreeSave)
            .filter(SpreeSave.spree_id == spree_id, SpreeSave.user_id == user_id)
            .first()
        )

    def add_save(self, spree_id: str, user_id: str) -> SpreeSave:
        existing = self.get_save(spree_id=spree_id, user_id=user_id)
        if existing:
            return existing

        save = SpreeSave(spree_id=spree_id, user_id=user_id)
        try:
            self.db.add(save)
            self.db.commit()
            self.db.refresh(save)
            return save
        except IntegrityError:
            self.db.rollback()
            found = self.get_save(spree_id=spree_id, user_id=user_id)
            if found:
                return found
            raise
        except Exception:
            self.db.rollback()
            raise

    def remove_save(self, spree_id: str, user_id: str) -> bool:
        save = self.get_save(spree_id=spree_id, user_id=user_id)
        if not save:
            return False
        try:
            self.db.delete(save)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise
