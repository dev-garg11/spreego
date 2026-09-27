from typing import List, Optional
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from src.models.moderation import Block, Mute, Report
from src.models.user import User
from src.repositories.base_repository import BaseRepository


class ModerationRepository:
    def __init__(self, db: Session):
        self.db = db
        self.report_repo = BaseRepository(Report, db)
        self.block_repo = BaseRepository(Block, db)
        self.mute_repo = BaseRepository(Mute, db)

    # Report operations
    def create_report(self, report: Report) -> Report:
        return self.report_repo.create(report)

    def get_report_by_id(self, report_id: str) -> Optional[Report]:
        return self.report_repo.get_by_id(report_id)

    # Block operations
    def get_block(self, blocker_id: str, blocked_id: str) -> Optional[Block]:
        return (
            self.db.query(Block)
            .filter(Block.blocker_id == blocker_id, Block.blocked_id == blocked_id)
            .first()
        )

    def create_block(self, blocker_id: str, blocked_id: str) -> Block:
        existing = self.get_block(blocker_id, blocked_id)
        if existing:
            return existing
        block = Block(blocker_id=blocker_id, blocked_id=blocked_id)
        try:
            self.db.add(block)
            self.db.commit()
            self.db.refresh(block)
            return block
        except IntegrityError:
            self.db.rollback()
            existing = self.get_block(blocker_id, blocked_id)
            if existing:
                return existing
            raise

    def delete_block(self, blocker_id: str, blocked_id: str) -> bool:
        block = self.get_block(blocker_id, blocked_id)
        if not block:
            return False
        try:
            self.db.delete(block)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise

    def get_blocked_users(self, blocker_id: str, skip: int = 0, limit: int = 50) -> List[Block]:
        return (
            self.db.query(Block)
            .options(joinedload(Block.blocked).joinedload(User.profile))
            .filter(Block.blocker_id == blocker_id)
            .order_by(Block.created_at.desc(), Block.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    # Mute operations
    def get_mute(self, muter_id: str, muted_id: str) -> Optional[Mute]:
        return (
            self.db.query(Mute)
            .filter(Mute.muter_id == muter_id, Mute.muted_id == muted_id)
            .first()
        )

    def create_mute(self, muter_id: str, muted_id: str) -> Mute:
        existing = self.get_mute(muter_id, muted_id)
        if existing:
            return existing
        mute = Mute(muter_id=muter_id, muted_id=muted_id)
        try:
            self.db.add(mute)
            self.db.commit()
            self.db.refresh(mute)
            return mute
        except IntegrityError:
            self.db.rollback()
            existing = self.get_mute(muter_id, muted_id)
            if existing:
                return existing
            raise

    def delete_mute(self, muter_id: str, muted_id: str) -> bool:
        mute = self.get_mute(muter_id, muted_id)
        if not mute:
            return False
        try:
            self.db.delete(mute)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise

    def get_muted_users(self, muter_id: str, skip: int = 0, limit: int = 50) -> List[Mute]:
        return (
            self.db.query(Mute)
            .options(joinedload(Mute.muted).joinedload(User.profile))
            .filter(Mute.muter_id == muter_id)
            .order_by(Mute.created_at.desc(), Mute.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
