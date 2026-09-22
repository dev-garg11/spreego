import base64
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.feed_controller import FeedController
from src.middlewares.auth_middleware import get_optional_current_user
from src.models.spree import SpreeType
from src.models.user import User
from src.validations.feed_schemas import FeedSpreeResponse

router = APIRouter(prefix="/api/v1/sprees", tags=["Feed"])


@router.get(
    "/feed",
    response_model=List[FeedSpreeResponse],
    status_code=status.HTTP_200_OK,
    summary="Get personalized discovery home feed",
)
@router.get(
    "/feed/",
    response_model=List[FeedSpreeResponse],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_feed(
    type: Optional[SpreeType] = Query(None, description="Optional filter by Spree type"),
    page: Optional[int] = Query(None, ge=1, le=10_000, description="Page number (1-indexed)"),
    skip: Optional[int] = Query(None, ge=0, le=100_000, description="Number of items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum items to return"),
    cursor: Optional[str] = Query(None, description="Optional cursor token or offset for pagination"),
    requesting_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> List[FeedSpreeResponse]:
    """
    Main personalized discovery home feed endpoint.
    Returns ranked Sprees driven by modular ranking engine (freshness decay,
    engagement signals, watch quality, creator affinity, and Buzzer boost multipliers).
    Supports pagination by page/limit, skip/limit, or cursor.
    """
    if cursor is not None:
        cursor_str = cursor.strip()
        if not cursor_str:
            offset = 0
        elif cursor_str.isdigit():
            offset = int(cursor_str)
            if offset > 100_000:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cursor offset exceeds maximum allowable window.",
                )
        else:
            try:
                # Support both padded and unpadded URL-safe base64 tokens
                padded = cursor_str + "=" * ((4 - len(cursor_str) % 4) % 4)
                decoded = base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8")
                offset = int(decoded)
                if offset < 0 or offset > 100_000:
                    raise ValueError("Offset out of allowable range.")
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid cursor pagination parameter.",
                )
    elif page is not None:
        offset = (page - 1) * limit
    else:
        offset = skip or 0

    return FeedController.get_feed(
        requesting_user=requesting_user,
        spree_type=type,
        skip=offset,
        limit=limit,
        db=db,
    )
