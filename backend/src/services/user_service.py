from typing import List, Optional
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from src.models.follow import Follow
from src.models.profile import Profile
from src.models.user import User
from src.repositories.follow_repository import FollowRepository
from src.repositories.profile_repository import ProfileRepository
from src.repositories.user_repository import UserRepository
from src.validations.user_schemas import (
    FollowUserItem,
    UpdateProfileRequest,
    UserProfileResponse,
)


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.profile_repo = ProfileRepository(db)
        self.follow_repo = FollowRepository(db)

    def get_user_profile(self, user_id: str) -> UserProfileResponse:
        user = self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise LookupError("User not found.")

        profile = user.profile
        followers_count = self.follow_repo.count_followers(user.id)
        following_count = self.follow_repo.count_following(user.id)

        return UserProfileResponse(
            id=user.id,
            username=profile.username if profile else None,
            full_name=profile.full_name if profile else None,
            bio=profile.bio if profile else None,
            avatar_url=profile.avatar_url if profile else None,
            followers_count=followers_count,
            following_count=following_count,
        )

    def update_profile(self, user: User, payload: UpdateProfileRequest) -> UserProfileResponse:
        profile = self.profile_repo.get_by_user_id(user.id)
        is_new = False
        if not profile:
            is_new = True
            profile = Profile(user_id=user.id)

        update_data = payload.model_dump(exclude_unset=True)

        if "username" in update_data:
            new_username = update_data["username"]
            if new_username is None or not str(new_username).strip():
                raise ValueError("Username cannot be empty.")
            new_username = str(new_username).strip()
            if profile.username != new_username:
                existing = self.profile_repo.get_by_username(new_username)
                if existing and existing.user_id != user.id:
                    raise ValueError("Username already taken.")
            update_data["username"] = new_username

        if "full_name" in update_data and update_data["full_name"] is not None:
            update_data["full_name"] = update_data["full_name"].strip()

        for key, value in update_data.items():
            setattr(profile, key, value)

        try:
            if is_new:
                self.profile_repo.create(profile)
            else:
                self.profile_repo.update(profile)
        except IntegrityError:
            raise ValueError("Username already taken.")

        followers_count = self.follow_repo.count_followers(user.id)
        following_count = self.follow_repo.count_following(user.id)

        return UserProfileResponse(
            id=user.id,
            username=profile.username,
            full_name=profile.full_name,
            bio=profile.bio,
            avatar_url=profile.avatar_url,
            followers_count=followers_count,
            following_count=following_count,
        )

    def follow_user(self, follower_id: str, target_user_id: str) -> None:
        if follower_id == target_user_id:
            raise ValueError("You cannot follow yourself.")

        target_user = self.user_repo.get_by_id(target_user_id)
        if not target_user or not target_user.is_active:
            raise LookupError("User not found.")

        existing = self.follow_repo.get_follow(follower_id, target_user_id)
        if existing:
            raise ValueError("You are already following this user.")

        follow = Follow(follower_id=follower_id, following_id=target_user_id)
        try:
            self.follow_repo.create(follow)
        except IntegrityError:
            raise ValueError("You are already following this user.")

    def unfollow_user(self, follower_id: str, target_user_id: str) -> None:
        if follower_id == target_user_id:
            raise ValueError("You cannot unfollow yourself.")

        target_user = self.user_repo.get_by_id(target_user_id)
        if not target_user or not target_user.is_active:
            raise LookupError("User not found.")

        follow = self.follow_repo.get_follow(follower_id, target_user_id)
        if not follow:
            raise ValueError("You are not following this user.")

        self.follow_repo.delete(follow)

    def get_followers(self, user_id: str, skip: int = 0, limit: int = 20) -> List[FollowUserItem]:
        user = self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise LookupError("User not found.")

        follows = self.follow_repo.get_followers(user_id, skip=skip, limit=limit)
        results = []
        for f in follows:
            u = f.follower
            p = u.profile if u else None
            results.append(
                FollowUserItem(
                    id=u.id if u else f.follower_id,
                    username=p.username if p else None,
                    full_name=p.full_name if p else None,
                    bio=p.bio if p else None,
                    avatar_url=p.avatar_url if p else None,
                )
            )
        return results

    def get_following(self, user_id: str, skip: int = 0, limit: int = 20) -> List[FollowUserItem]:
        user = self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise LookupError("User not found.")

        follows = self.follow_repo.get_following(user_id, skip=skip, limit=limit)
        results = []
        for f in follows:
            u = f.following
            p = u.profile if u else None
            results.append(
                FollowUserItem(
                    id=u.id if u else f.following_id,
                    username=p.username if p else None,
                    full_name=p.full_name if p else None,
                    bio=p.bio if p else None,
                    avatar_url=p.avatar_url if p else None,
                )
            )
        return results
