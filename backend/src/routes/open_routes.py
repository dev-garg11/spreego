from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.open_controller import OpenController
from src.middlewares.auth_middleware import get_current_user
from src.models.open import OpenStatus, OpenType
from src.models.user import User
from src.validations.feed_schemas import FeedSpreeResponse
from src.validations.open_schemas import (
    CreateOpenRequest,
    JoinOpenResponse,
    OpenRankingItem,
    OpenResponse,
    OpenSubmissionResponse,
    SubmitSpreeRequest,
)

router = APIRouter(prefix="/api/v1/opens", tags=["Opens"])


# ============================================================================
# 1. Create Open (POST /api/v1/opens)
# ============================================================================

@router.post(
    "",
    response_model=OpenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Open challenge or competition",
)
@router.post(
    "/",
    response_model=OpenResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_open(
    payload: CreateOpenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OpenResponse:
    """Authenticated endpoint to create a new Open. Creator ID is strictly derived from JWT."""
    return OpenController.create_open(
        current_user=current_user,
        payload=payload,
        db=db,
    )


# ============================================================================
# 2. List Opens (GET /api/v1/opens)
# ============================================================================

@router.get(
    "",
    response_model=List[OpenResponse],
    status_code=status.HTTP_200_OK,
    summary="List Opens with optional filtering and pagination",
)
@router.get(
    "/",
    response_model=List[OpenResponse],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def list_opens(
    type: Optional[OpenType] = Query(None, description="Optional filter by Open type"),
    status: Optional[OpenStatus] = Query(None, description="Optional filter by Open status"),
    page: Optional[int] = Query(None, ge=1, description="Page number (1-indexed)"),
    skip: Optional[int] = Query(None, ge=0, description="Number of items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum items to return"),
    db: Session = Depends(get_db),
) -> List[OpenResponse]:
    """Paginated list of Opens with optional filtering by type and status."""
    offset = (page - 1) * limit if page is not None else (skip if skip is not None else 0)
    return OpenController.list_opens(
        open_type=type,
        open_status=status,
        skip=offset,
        limit=limit,
        db=db,
    )


# ============================================================================
# 3. Get Single Open (GET /api/v1/opens/{id})
# ============================================================================

@router.get(
    "/{id}",
    response_model=OpenResponse,
    status_code=status.HTTP_200_OK,
    summary="Get detailed view of a single Open",
)
@router.get(
    "/{id}/",
    response_model=OpenResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_open(
    id: str,
    db: Session = Depends(get_db),
) -> OpenResponse:
    """Detailed view of a single Open including rules, dates, scoring config, and participant count."""
    return OpenController.get_open(open_id=id, db=db)


# ============================================================================
# 4. Join Open (POST /api/v1/opens/{id}/join)
# ============================================================================

@router.post(
    "/{id}/join",
    response_model=JoinOpenResponse,
    status_code=status.HTTP_200_OK,
    summary="Join an active Open challenge",
)
@router.post(
    "/{id}/join/",
    response_model=JoinOpenResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def join_open(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JoinOpenResponse:
    """Authenticated endpoint to join an Open. Validates status, dates, and max participant limit."""
    return OpenController.join_open(open_id=id, current_user=current_user, db=db)


# ============================================================================
# 5. Submit Spree (POST /api/v1/opens/{id}/submissions)
# ============================================================================

@router.post(
    "/{id}/submissions",
    response_model=OpenSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a Spree to an Open",
)
@router.post(
    "/{id}/submissions/",
    response_model=OpenSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def submit_spree(
    id: str,
    payload: SubmitSpreeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OpenSubmissionResponse:
    """
    Authenticated endpoint to submit a Spree to an Open.
    Verifies creator ownership, active dates, and prevents duplicate submissions.
    """
    return OpenController.submit_spree(
        open_id=id,
        payload=payload,
        current_user=current_user,
        db=db,
    )


# ============================================================================
# 6. VIEW Feed (GET /api/v1/opens/{id}/feed)
# ============================================================================

@router.get(
    "/{id}/feed",
    response_model=List[FeedSpreeResponse],
    status_code=status.HTTP_200_OK,
    summary="VIEW Feed: Dedicated feed containing ONLY Sprees submitted to this Open",
)
@router.get(
    "/{id}/feed/",
    response_model=List[FeedSpreeResponse],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_open_feed(
    id: str,
    page: Optional[int] = Query(None, ge=1, description="Page number (1-indexed)"),
    skip: Optional[int] = Query(None, ge=0, description="Number of items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum items to return"),
    db: Session = Depends(get_db),
) -> List[FeedSpreeResponse]:
    """VIEW Feed: returns ONLY Sprees submitted to this specific Open."""
    offset = (page - 1) * limit if page is not None else (skip if skip is not None else 0)
    return OpenController.get_feed(open_id=id, skip=offset, limit=limit, db=db)


# ============================================================================
# 7. RANKING Leaderboard (GET /api/v1/opens/{id}/ranking)
# ============================================================================

@router.get(
    "/{id}/ranking",
    response_model=List[OpenRankingItem],
    status_code=status.HTTP_200_OK,
    summary="RANKING Leaderboard: Dynamic real-time calculated ranking driven by scoring_config",
)
@router.get(
    "/{id}/ranking/",
    response_model=List[OpenRankingItem],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_open_ranking(
    id: str,
    db: Session = Depends(get_db),
) -> List[OpenRankingItem]:
    """
    RANKING Leaderboard: Real-time calculated creator ranking (Rank 1, Rank 2, Score)
    driven dynamically by the Open's stored scoring_config.
    """
    return OpenController.get_ranking(open_id=id, db=db)
