from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from src.models.engagement import SpreeShare, SpreeView, SpreeComment
from src.repositories.engagement_repository import EngagementRepository
from src.validations.engagement_schemas import (
    CommentResponse,
    CommentUserProfile,
    CreateCommentRequest,
    RecordShareRequest,
    RecordViewRequest,
)


class EngagementService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EngagementRepository(db)

    def record_view(
        self,
        spree_id: str,
        user_id: Optional[str],
        payload: Optional[RecordViewRequest] = None,
    ) -> SpreeView:
        spree = self.repo.get_spree(spree_id)
        if not spree:
            raise LookupError("Spree not found.")

        watch_duration = payload.watch_duration if payload else 0.0
        completed = payload.completed if payload else False

        return self.repo.record_view(
            spree_id=spree_id,
            user_id=user_id,
            watch_duration=watch_duration,
            completed=completed,
        )

    def clap_spree(self, spree_id: str, user_id: str) -> None:
        spree = self.repo.get_spree(spree_id)
        if not spree:
            raise LookupError("Spree not found.")
        self.repo.add_clap(spree_id=spree_id, user_id=user_id)

    def unclap_spree(self, spree_id: str, user_id: str) -> None:
        spree = self.repo.get_spree(spree_id)
        if not spree:
            raise LookupError("Spree not found.")
        self.repo.remove_clap(spree_id=spree_id, user_id=user_id)

    def create_comment(
        self,
        spree_id: str,
        user_id: str,
        payload: CreateCommentRequest,
    ) -> CommentResponse:
        spree = self.repo.get_spree(spree_id)
        if not spree:
            raise LookupError("Spree not found.")

        text = payload.text.strip()
        if not text:
            raise ValueError("Comment text cannot be empty.")

        parent_id = (
            payload.parent_id.strip()
            if payload and payload.parent_id and payload.parent_id.strip()
            else None
        )

        if parent_id:
            parent = self.repo.get_comment_by_id(parent_id)
            if not parent or parent.spree_id != spree_id:
                raise LookupError("Parent comment not found on this spree.")

        created = self.repo.create_comment(
            spree_id=spree_id,
            user_id=user_id,
            text=text,
            parent_id=parent_id,
        )
        # Fetch with eager profile
        comment = self.repo.get_comment_by_id(created.id) or created
        return self._to_comment_response(comment)

    def get_comments(
        self,
        spree_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> List[CommentResponse]:
        spree = self.repo.get_spree(spree_id)
        if not spree:
            raise LookupError("Spree not found.")

        comments = self.repo.get_comments(spree_id=spree_id, skip=skip, limit=limit)
        return [self._to_comment_response(c) for c in comments]

    def record_share(
        self,
        spree_id: str,
        user_id: Optional[str],
        payload: Optional[RecordShareRequest] = None,
    ) -> Tuple[SpreeShare, int]:
        spree = self.repo.get_spree(spree_id)
        if not spree:
            raise LookupError("Spree not found.")

        platform = (
            payload.platform.strip()
            if payload and payload.platform and payload.platform.strip()
            else None
        )
        share = self.repo.record_share(spree_id=spree_id, user_id=user_id, platform=platform)
        share_count = self.repo.count_shares(spree_id=spree_id)
        return share, share_count

    def save_spree(self, spree_id: str, user_id: str) -> None:
        spree = self.repo.get_spree(spree_id)
        if not spree:
            raise LookupError("Spree not found.")
        self.repo.add_save(spree_id=spree_id, user_id=user_id)

    def unsave_spree(self, spree_id: str, user_id: str) -> None:
        spree = self.repo.get_spree(spree_id)
        if not spree:
            raise LookupError("Spree not found.")
        self.repo.remove_save(spree_id=spree_id, user_id=user_id)

    def _to_comment_response(self, comment: SpreeComment) -> CommentResponse:
        username = None
        avatar_url = None
        full_name = None

        if comment.user and getattr(comment.user, "profile", None):
            profile = comment.user.profile
            username = profile.username
            avatar_url = profile.avatar_url
            full_name = profile.full_name

        user_profile = (
            CommentUserProfile(
                id=comment.user_id,
                username=username,
                avatar_url=avatar_url,
                full_name=full_name,
            )
            if comment.user
            else None
        )

        return CommentResponse(
            id=comment.id,
            spree_id=comment.spree_id,
            user_id=comment.user_id,
            text=comment.text,
            parent_id=comment.parent_id,
            created_at=comment.created_at,
            username=username,
            avatar_url=avatar_url,
            user=user_profile,
        )
