from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from src.models.user import User
from src.services.user_service import UserService
from src.validations.auth_schemas import MessageResponse
from src.validations.user_schemas import (
    FollowUserItem,
    UpdateProfileRequest,
    UserProfileResponse,
)


class UserController:
    @staticmethod
    def get_user_profile(user_id: str, db: Session) -> UserProfileResponse:
        service = UserService(db)
        try:
            return service.get_user_profile(user_id)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def update_profile(
        current_user: User,
        payload: UpdateProfileRequest,
        db: Session,
    ) -> UserProfileResponse:
        service = UserService(db)
        try:
            return service.update_profile(current_user, payload)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def follow_user(
        user_id: str,
        current_user: User,
        db: Session,
    ) -> MessageResponse:
        service = UserService(db)
        try:
            service.follow_user(follower_id=current_user.id, target_user_id=user_id)
            return MessageResponse(message="User followed successfully.")
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def unfollow_user(
        user_id: str,
        current_user: User,
        db: Session,
    ) -> MessageResponse:
        service = UserService(db)
        try:
            service.unfollow_user(follower_id=current_user.id, target_user_id=user_id)
            return MessageResponse(message="User unfollowed successfully.")
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def get_followers(
        user_id: str,
        skip: int,
        limit: int,
        db: Session,
    ) -> List[FollowUserItem]:
        service = UserService(db)
        try:
            return service.get_followers(user_id=user_id, skip=skip, limit=limit)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def get_following(
        user_id: str,
        skip: int,
        limit: int,
        db: Session,
    ) -> List[FollowUserItem]:
        service = UserService(db)
        try:
            return service.get_following(user_id=user_id, skip=skip, limit=limit)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
