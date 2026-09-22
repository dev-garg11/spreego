from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.spree_controller import SpreeController
from src.middlewares.auth_middleware import get_current_user, get_optional_current_user
from src.models.spree import SpreeType
from src.models.user import User
from src.validations.auth_schemas import MessageResponse
from src.validations.spree_schemas import (
    CreateSpreeRequest,
    SpreeResponse,
    UpdateSpreeRequest,
)

router = APIRouter(prefix="/api/v1/sprees", tags=["Sprees"])


@router.post(
    "",
    response_model=SpreeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Spree",
)
@router.post(
    "/",
    response_model=SpreeResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_spree(
    payload: CreateSpreeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SpreeResponse:
    """Authenticated endpoint to create a new Spree. Creator ID is strictly derived from the current user."""
    return SpreeController.create_spree(current_user=current_user, payload=payload, db=db)


@router.get(
    "",
    response_model=List[SpreeResponse],
    status_code=status.HTTP_200_OK,
    summary="List public sprees",
)
@router.get(
    "/",
    response_model=List[SpreeResponse],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def list_sprees(
    type: Optional[SpreeType] = Query(None, description="Filter by Spree type"),
    page: Optional[int] = Query(None, ge=1, description="Page number (1-indexed)"),
    skip: Optional[int] = Query(None, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum records to return"),
    db: Session = Depends(get_db),
) -> List[SpreeResponse]:
    """Paginated list of public sprees with optional filter by content type."""
    offset = (page - 1) * limit if page is not None else (skip if skip is not None else 0)
    return SpreeController.list_public_sprees(spree_type=type, skip=offset, limit=limit, db=db)


@router.get(
    "/{id}",
    response_model=SpreeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a single Spree by ID",
)
@router.get(
    "/{id}/",
    response_model=SpreeResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_spree(
    id: str,
    requesting_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> SpreeResponse:
    """Public lookup of a single Spree by ID with visibility checks for PRIVATE and FOLLOWERS_ONLY sprees."""
    return SpreeController.get_spree(spree_id=id, requesting_user=requesting_user, db=db)


@router.patch(
    "/{id}",
    response_model=SpreeResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Spree details",
)
@router.patch(
    "/{id}/",
    response_model=SpreeResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def update_spree(
    id: str,
    payload: UpdateSpreeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SpreeResponse:
    """Authenticated endpoint to update Spree details. Only the creator can update."""
    return SpreeController.update_spree(spree_id=id, current_user=current_user, payload=payload, db=db)


@router.delete(
    "/{id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a Spree",
)
@router.delete(
    "/{id}/",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def delete_spree(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Authenticated endpoint to delete a Spree. Only the creator can delete."""
    return SpreeController.delete_spree(spree_id=id, current_user=current_user, db=db)
