from typing import List, Optional
from sqlalchemy.orm import Session
from src.models.moderation import Block, Mute, Report, ReportEntityType, ReportReason
from src.models.user import User
from src.repositories.moderation_repository import ModerationRepository
from src.repositories.user_repository import UserRepository
from src.validations.auth_schemas import MessageResponse
from src.validations.moderation_schemas import (
    BlockedUserItem,
    BlockResponse,
    CreateReportRequest,
    MutedUserItem,
    MuteResponse,
    ReportResponse,
)


class ModerationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ModerationRepository(db)
        self.user_repo = UserRepository(db)

    def create_report(
        self,
        current_user: User,
        payload: CreateReportRequest,
    ) -> Report:
        entity_id = payload.entity_id.strip() if payload.entity_id else ""
        if not entity_id:
            raise ValueError("entity_id cannot be blank.")
        if payload.entity_type == ReportEntityType.USER and (entity_id == current_user.id or entity_id.lower() == "me"):
            raise ValueError("You cannot report yourself.")

        report = Report(
            reporter_id=current_user.id,
            entity_id=entity_id,
            entity_type=payload.entity_type,
            reason=payload.reason,
            description=payload.description.strip() if payload.description and payload.description.strip() else None,
        )
        return self.repo.create_report(report)

    def block_user(self, current_user: User, target_user_id: str) -> BlockResponse:
        target_id = target_user_id.strip() if target_user_id else ""
        if not target_id:
            raise ValueError("target_user_id cannot be blank.")
        if target_id == current_user.id or target_id.lower() == "me":
            raise ValueError("You cannot block yourself.")

        target = self.user_repo.get_by_id(target_id)
        if not target or not target.is_active:
            raise LookupError("User not found.")

        block = self.repo.create_block(blocker_id=current_user.id, blocked_id=target_id)
        return BlockResponse(
            id=block.id,
            blocker_id=block.blocker_id,
            blocked_id=block.blocked_id,
            created_at=block.created_at,
            message="User blocked successfully.",
        )

    def unblock_user(self, current_user: User, target_user_id: str) -> MessageResponse:
        target_id = target_user_id.strip() if target_user_id else ""
        if not target_id:
            raise ValueError("target_user_id cannot be blank.")
        if target_id == current_user.id or target_id.lower() == "me":
            raise ValueError("You cannot unblock yourself.")

        # If a block exists, remove it unconditionally (even if target was deactivated)
        block = self.repo.get_block(blocker_id=current_user.id, blocked_id=target_id)
        if block:
            self.repo.delete_block(blocker_id=current_user.id, blocked_id=target_id)
            return MessageResponse(message="User unblocked successfully.")

        # If no block exists, verify whether the target user even exists
        target = self.user_repo.get_by_id(target_id)
        if not target:
            raise LookupError("User not found.")

        return MessageResponse(message="User unblocked successfully.")

    def get_blocked_users(
        self, current_user: User, skip: int = 0, limit: int = 50
    ) -> List[BlockedUserItem]:
        blocks = self.repo.get_blocked_users(blocker_id=current_user.id, skip=skip, limit=limit)
        items = []
        for b in blocks:
            blocked_user = b.blocked if b.blocked is not None else self.user_repo.get_by_id(b.blocked_id)
            profile = blocked_user.profile if blocked_user else None
            items.append(
                BlockedUserItem(
                    id=b.blocked_id,
                    user_id=b.blocked_id,
                    blocked_id=b.blocked_id,
                    username=profile.username if profile else None,
                    full_name=profile.full_name if profile else None,
                    bio=profile.bio if profile else None,
                    avatar_url=profile.avatar_url if profile else None,
                    created_at=b.created_at,
                )
            )
        return items

    def mute_user(self, current_user: User, target_user_id: str) -> MuteResponse:
        target_id = target_user_id.strip() if target_user_id else ""
        if not target_id:
            raise ValueError("target_user_id cannot be blank.")
        if target_id == current_user.id or target_id.lower() == "me":
            raise ValueError("You cannot mute yourself.")

        target = self.user_repo.get_by_id(target_id)
        if not target or not target.is_active:
            raise LookupError("User not found.")

        mute = self.repo.create_mute(muter_id=current_user.id, muted_id=target_id)
        return MuteResponse(
            id=mute.id,
            muter_id=mute.muter_id,
            muted_id=mute.muted_id,
            created_at=mute.created_at,
            message="User muted successfully.",
        )

    def unmute_user(self, current_user: User, target_user_id: str) -> MessageResponse:
        target_id = target_user_id.strip() if target_user_id else ""
        if not target_id:
            raise ValueError("target_user_id cannot be blank.")
        if target_id == current_user.id or target_id.lower() == "me":
            raise ValueError("You cannot unmute yourself.")

        # If a mute exists, remove it unconditionally (even if target was deactivated)
        mute = self.repo.get_mute(muter_id=current_user.id, muted_id=target_id)
        if mute:
            self.repo.delete_mute(muter_id=current_user.id, muted_id=target_id)
            return MessageResponse(message="User unmuted successfully.")

        # If no mute exists, verify whether the target user even exists
        target = self.user_repo.get_by_id(target_id)
        if not target:
            raise LookupError("User not found.")

        return MessageResponse(message="User unmuted successfully.")

    def get_muted_users(
        self, current_user: User, skip: int = 0, limit: int = 50
    ) -> List[MutedUserItem]:
        mutes = self.repo.get_muted_users(muter_id=current_user.id, skip=skip, limit=limit)
        items = []
        for m in mutes:
            muted_user = m.muted if m.muted is not None else self.user_repo.get_by_id(m.muted_id)
            profile = muted_user.profile if muted_user else None
            items.append(
                MutedUserItem(
                    id=m.muted_id,
                    user_id=m.muted_id,
                    muted_id=m.muted_id,
                    username=profile.username if profile else None,
                    full_name=profile.full_name if profile else None,
                    bio=profile.bio if profile else None,
                    avatar_url=profile.avatar_url if profile else None,
                    created_at=m.created_at,
                )
            )
        return items
