from typing import List, Optional
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload
from src.models.open import Open, OpenParticipant, OpenStatus, OpenSubmission, OpenType
from src.repositories.base_repository import BaseRepository


class OpenRepository(BaseRepository[Open]):
    def __init__(self, db: Session):
        super().__init__(Open, db)

    def get_by_id(self, id: str) -> Optional[Open]:
        return (
            self.db.query(Open)
            .options(
                joinedload(Open.creator),
                selectinload(Open.participants),
                selectinload(Open.submissions),
            )
            .filter(Open.id == id)
            .first()
        )

    def get_opens(
        self,
        open_type: Optional[OpenType] = None,
        open_status: Optional[OpenStatus] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Open]:
        query = self.db.query(Open).options(
            joinedload(Open.creator),
            selectinload(Open.participants),
            selectinload(Open.submissions),
        )
        if open_type is not None:
            query = query.filter(Open.type == open_type)
        if open_status is not None:
            query = query.filter(Open.status == open_status)
        return query.order_by(Open.created_at.desc(), Open.id.desc()).offset(skip).limit(limit).all()

    def count_opens(
        self,
        open_type: Optional[OpenType] = None,
        open_status: Optional[OpenStatus] = None,
    ) -> int:
        query = self.db.query(Open)
        if open_type is not None:
            query = query.filter(Open.type == open_type)
        if open_status is not None:
            query = query.filter(Open.status == open_status)
        return query.count()

    def add_participant(self, open_id: str, user_id: str) -> OpenParticipant:
        participant = OpenParticipant(open_id=open_id, user_id=user_id)
        try:
            self.db.add(participant)
            self.db.commit()
            self.db.refresh(participant)
            return participant
        except IntegrityError:
            self.db.rollback()
            raise ValueError("You have already joined this Open.")
        except Exception:
            self.db.rollback()
            raise

    def get_participant(self, open_id: str, user_id: str) -> Optional[OpenParticipant]:
        return (
            self.db.query(OpenParticipant)
            .filter(
                OpenParticipant.open_id == open_id,
                OpenParticipant.user_id == user_id,
            )
            .first()
        )

    def count_participants(self, open_id: str) -> int:
        return self.db.query(OpenParticipant).filter(OpenParticipant.open_id == open_id).count()

    def add_submission(
        self,
        open_id: str,
        user_id: str,
        spree_id: str,
        score: float = 0.0,
    ) -> OpenSubmission:
        submission = OpenSubmission(
            open_id=open_id,
            user_id=user_id,
            spree_id=spree_id,
            score=score,
        )
        try:
            self.db.add(submission)
            self.db.commit()
            self.db.refresh(submission)
            return submission
        except IntegrityError:
            self.db.rollback()
            raise ValueError("This Spree has already been submitted to this Open.")
        except Exception:
            self.db.rollback()
            raise

    def get_submission_by_spree(self, open_id: str, spree_id: str) -> Optional[OpenSubmission]:
        return (
            self.db.query(OpenSubmission)
            .filter(
                OpenSubmission.open_id == open_id,
                OpenSubmission.spree_id == spree_id,
            )
            .first()
        )

    def get_submissions_for_open(
        self,
        open_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[OpenSubmission]:
        return (
            self.db.query(OpenSubmission)
            .options(
                joinedload(OpenSubmission.user),
                joinedload(OpenSubmission.spree),
            )
            .filter(OpenSubmission.open_id == open_id)
            .order_by(OpenSubmission.created_at.desc(), OpenSubmission.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_submissions(self, open_id: str) -> int:
        return self.db.query(OpenSubmission).filter(OpenSubmission.open_id == open_id).count()
