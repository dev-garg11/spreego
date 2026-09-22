from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.user_controller import UserController
from src.middlewares.auth_middleware import get_current_user
from src.models.user import User
from src.validations.auth_schemas import MessageResponse
from src.validations.user_schemas import (
    FollowUserItem,
    UpdateProfileRequest,
    UserProfileResponse,
)

router = APIRouter(prefix="/api/v1/users", tags=["Users & Profiles"])


@router.patch(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update authenticated user profile",
)
def update_profile(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    return UserController.update_profile(current_user=current_user, payload=payload, db=db)


@router.get(
    "/{id}",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get public user profile",
)
def get_user_profile(
    id: str,
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    return UserController.get_user_profile(user_id=id, db=db)


@router.post(
    "/{id}/follow",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Follow a user",
)
def follow_user(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    return UserController.follow_user(user_id=id, current_user=current_user, db=db)


@router.delete(
    "/{id}/follow",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Unfollow a user",
)
def unfollow_user(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    return UserController.unfollow_user(user_id=id, current_user=current_user, db=db)


@router.get(
    "/{id}/followers",
    response_model=List[FollowUserItem],
    status_code=status.HTTP_200_OK,
    summary="Get user followers",
)
def get_followers(
    id: str,
    page: Optional[int] = Query(None, ge=1, description="Page number (1-indexed)"),
    skip: Optional[int] = Query(None, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum records to return"),
    db: Session = Depends(get_db),
) -> List[FollowUserItem]:
    offset = (page - 1) * limit if page is not None else (skip or 0)
    return UserController.get_followers(user_id=id, skip=offset, limit=limit, db=db)


@router.get(
    "/{id}/following",
    response_model=List[FollowUserItem],
    status_code=status.HTTP_200_OK,
    summary="Get user following",
)
def get_following(
    id: str,
    page: Optional[int] = Query(None, ge=1, description="Page number (1-indexed)"),
    skip: Optional[int] = Query(None, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum records to return"),
    db: Session = Depends(get_db),
) -> List[FollowUserItem]:
    offset = (page - 1) * limit if page is not None else (skip or 0)
    return UserController.get_following(user_id=id, skip=offset, limit=limit, db=db)
