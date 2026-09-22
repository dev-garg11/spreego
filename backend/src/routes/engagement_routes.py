from typing import List, Optional
from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.engagement_controller import EngagementController
from src.middlewares.auth_middleware import get_current_user, get_optional_current_user
from src.models.user import User
from src.validations.engagement_schemas import (
    ClapResponse,
    CommentResponse,
    CreateCommentRequest,
    RecordShareRequest,
    RecordViewRequest,
    SaveResponse,
    ShareResponse,
    UnclapResponse,
    UnsaveResponse,
    ViewResponse,
)

router = APIRouter(prefix="/api/v1/sprees/{id}", tags=["Engagement"])


# ============================================================================
# Views
# ============================================================================

@router.post(
    "/view",
    response_model=ViewResponse,
    status_code=status.HTTP_200_OK,
    summary="Record a real view with watch metrics",
)
@router.post(
    "/view/",
    response_model=ViewResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def record_view(
    id: str,
    payload: Optional[RecordViewRequest] = Body(None),
    requesting_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> ViewResponse:
    """Record a real spree view event with optional watch duration and completion metrics."""
    return EngagementController.record_view(
        spree_id=id,
        user=requesting_user,
        payload=payload,
        db=db,
    )


# ============================================================================
# Claps
# ============================================================================

@router.post(
    "/clap",
    response_model=ClapResponse,
    status_code=status.HTTP_200_OK,
    summary="Clap a Spree (idempotent)",
)
@router.post(
    "/clap/",
    response_model=ClapResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def clap_spree(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClapResponse:
    """Authenticated duplicate-safe endpoint to clap a Spree."""
    return EngagementController.clap_spree(
        spree_id=id,
        current_user=current_user,
        db=db,
    )


@router.delete(
    "/clap",
    response_model=UnclapResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove a clap from a Spree",
)
@router.delete(
    "/clap/",
    response_model=UnclapResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def unclap_spree(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UnclapResponse:
    """Authenticated endpoint to remove a user's clap from a Spree."""
    return EngagementController.unclap_spree(
        spree_id=id,
        current_user=current_user,
        db=db,
    )


# ============================================================================
# Comments
# ============================================================================

@router.get(
    "/comments",
    response_model=List[CommentResponse],
    status_code=status.HTTP_200_OK,
    summary="Get paginated comments for a Spree",
)
@router.get(
    "/comments/",
    response_model=List[CommentResponse],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_comments(
    id: str,
    page: Optional[int] = Query(None, ge=1, description="Page number (1-indexed)"),
    skip: Optional[int] = Query(None, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum records to return"),
    db: Session = Depends(get_db),
) -> List[CommentResponse]:
    """Paginated comments list for a Spree including commenter usernames and avatars."""
    offset = (page - 1) * limit if page is not None else (skip or 0)
    return EngagementController.get_comments(
        spree_id=id,
        skip=offset,
        limit=limit,
        db=db,
    )


@router.post(
    "/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Post a comment on a Spree",
)
@router.post(
    "/comments/",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_comment(
    id: str,
    payload: CreateCommentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CommentResponse:
    """Authenticated endpoint to post a top-level comment or reply to an existing comment."""
    return EngagementController.create_comment(
        spree_id=id,
        current_user=current_user,
        payload=payload,
        db=db,
    )


# ============================================================================
# Shares
# ============================================================================

@router.post(
    "/share",
    response_model=ShareResponse,
    status_code=status.HTTP_200_OK,
    summary="Record a share event for a Spree",
)
@router.post(
    "/share/",
    response_model=ShareResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def record_share(
    id: str,
    payload: Optional[RecordShareRequest] = Body(None),
    requesting_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> ShareResponse:
    """Record a share event and return updated share metrics."""
    return EngagementController.record_share(
        spree_id=id,
        user=requesting_user,
        payload=payload,
        db=db,
    )


# ============================================================================
# Saves / Bookmarks
# ============================================================================

@router.post(
    "/save",
    response_model=SaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Save/bookmark a Spree (idempotent)",
)
@router.post(
    "/save/",
    response_model=SaveResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def save_spree(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SaveResponse:
    """Authenticated duplicate-safe endpoint to bookmark/save a Spree."""
    return EngagementController.save_spree(
        spree_id=id,
        current_user=current_user,
        db=db,
    )


@router.delete(
    "/save",
    response_model=UnsaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove a saved Spree bookmark",
)
@router.delete(
    "/save/",
    response_model=UnsaveResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def unsave_spree(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UnsaveResponse:
    """Authenticated endpoint to remove a saved bookmark from a Spree."""
    return EngagementController.unsave_spree(
        spree_id=id,
        current_user=current_user,
        db=db,
    )
