from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from src.models.spree import Spree, SpreeType, SpreeVisibility
from src.models.user import User
from src.repositories.follow_repository import FollowRepository
from src.repositories.spree_repository import SpreeRepository
from src.repositories.user_repository import UserRepository
from src.validations.spree_schemas import CreateSpreeRequest, UpdateSpreeRequest


class AuthenticationRequiredError(Exception):
    """Raised when an unauthenticated client requests protected content."""
    pass


class SpreeService:
    def __init__(self, db: Session):
        self.db = db
        self.spree_repo = SpreeRepository(db)
        self.user_repo = UserRepository(db)
        self.follow_repo = FollowRepository(db)

    def create_spree(self, creator_id: str, payload: CreateSpreeRequest) -> Spree:
        creator = self.user_repo.get_by_id(creator_id)
        if not creator or not creator.is_active:
            raise LookupError("User not found.")

        title = payload.title.strip()
        media_url = payload.media_url.strip()
        description = payload.description.strip() if payload.description and payload.description.strip() else None
        thumbnail_url = payload.thumbnail_url.strip() if payload.thumbnail_url and payload.thumbnail_url.strip() else None

        spree = Spree(
            creator_id=creator.id,
            type=payload.type,
            title=title,
            description=description,
            media_url=media_url,
            thumbnail_url=thumbnail_url,
            duration=payload.duration,
            visibility=payload.visibility if payload.visibility else SpreeVisibility.PUBLIC,
        )
        return self.spree_repo.create(spree)

    def get_spree(self, spree_id: str, requesting_user: Optional[User] = None) -> Spree:
        spree = self.spree_repo.get_by_id(spree_id)
        if not spree or not spree.creator or not spree.creator.is_active:
            raise LookupError("Spree not found.")

        # PUBLIC sprees can be viewed by anyone
        if spree.visibility == SpreeVisibility.PUBLIC:
            return spree

        # PRIVATE sprees can only be viewed by the creator
        if spree.visibility == SpreeVisibility.PRIVATE:
            if requesting_user is None:
                raise AuthenticationRequiredError("Authentication required to view this private spree.")
            if requesting_user.id != spree.creator_id:
                raise PermissionError("You do not have permission to view this private spree.")
            return spree

        # FOLLOWERS_ONLY sprees can be viewed by creator or verified followers
        if spree.visibility == SpreeVisibility.FOLLOWERS_ONLY:
            if requesting_user is None:
                raise AuthenticationRequiredError("Authentication required to view this spree.")
            if requesting_user.id == spree.creator_id:
                return spree

            follow = self.follow_repo.get_follow(
                follower_id=requesting_user.id,
                following_id=spree.creator_id,
            )
            if not follow:
                raise PermissionError("You must follow the creator to view this spree.")
            return spree

        return spree

    def update_spree(
        self,
        spree_id: str,
        current_user: User,
        payload: UpdateSpreeRequest,
    ) -> Spree:
        spree = self.spree_repo.get_by_id(spree_id)
        if not spree:
            raise LookupError("Spree not found.")

        # Strictly enforce ownership check
        if spree.creator_id != current_user.id:
            raise PermissionError("You do not have permission to update this spree.")

        update_data = payload.model_dump(exclude_unset=True)

        if "title" in update_data:
            val = update_data["title"]
            if val is None or not str(val).strip():
                raise ValueError("Title cannot be empty.")
            update_data["title"] = str(val).strip()

        if "media_url" in update_data:
            val = update_data["media_url"]
            if val is None or not str(val).strip():
                raise ValueError("Media URL cannot be empty.")
            update_data["media_url"] = str(val).strip()

        if "visibility" in update_data and update_data["visibility"] is None:
            raise ValueError("Visibility cannot be null.")

        if "description" in update_data and update_data["description"] is not None:
            clean_desc = str(update_data["description"]).strip()
            update_data["description"] = clean_desc if clean_desc else None

        if "thumbnail_url" in update_data and update_data["thumbnail_url"] is not None:
            clean_thumb = str(update_data["thumbnail_url"]).strip()
            update_data["thumbnail_url"] = clean_thumb if clean_thumb else None

        if "duration" in update_data and update_data["duration"] is not None:
            if update_data["duration"] < 0:
                raise ValueError("Duration cannot be negative.")

        ALLOWED_UPDATE_FIELDS = {
            "title",
            "description",
            "media_url",
            "thumbnail_url",
            "duration",
            "visibility",
        }
        for field, value in update_data.items():
            if field in ALLOWED_UPDATE_FIELDS:
                setattr(spree, field, value)

        spree.updated_at = datetime.now(timezone.utc)
        return self.spree_repo.update(spree)

    def delete_spree(self, spree_id: str, current_user: User) -> None:
        spree = self.spree_repo.get_by_id(spree_id)
        if not spree:
            raise LookupError("Spree not found.")

        # Strictly enforce ownership check
        if spree.creator_id != current_user.id:
            raise PermissionError("You do not have permission to delete this spree.")

        self.spree_repo.delete(spree)

    def list_public_sprees(
        self,
        spree_type: Optional[SpreeType] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Spree]:
        return self.spree_repo.get_public_sprees(
            spree_type=spree_type,
            skip=skip,
            limit=limit,
        )
