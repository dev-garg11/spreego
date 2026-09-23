from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.product_controller import ProductController
from src.middlewares.auth_middleware import get_current_user
from src.models.commerce import ProductType
from src.models.user import User
from src.validations.auth_schemas import MessageResponse
from src.validations.commerce_schemas import (
    CreateProductRequest,
    ProductResponse,
    UpdateProductRequest,
)

router = APIRouter(prefix="/api/v1/products", tags=["Products"])


@router.get(
    "",
    response_model=List[ProductResponse],
    status_code=status.HTTP_200_OK,
    summary="List products with optional filters",
)
@router.get(
    "/",
    response_model=List[ProductResponse],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def list_products(
    creator_id: Optional[str] = Query(None, description="Filter by creator user ID"),
    type: Optional[ProductType] = Query(None, description="Filter by product type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: Optional[int] = Query(None, ge=1, description="Page number (1-indexed)"),
    skip: Optional[int] = Query(None, ge=0, description="Offset"),
    limit: int = Query(20, ge=1, le=100, description="Page size limit"),
    db: Session = Depends(get_db),
) -> List[ProductResponse]:
    offset = (page - 1) * limit if page is not None else (skip if skip is not None else 0)
    return ProductController.list_products(
        creator_id=creator_id,
        product_type=type,
        is_active=is_active,
        skip=offset,
        limit=limit,
        db=db,
    )


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product (creator ID from JWT)",
)
@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_product(
    payload: CreateProductRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProductResponse:
    return ProductController.create_product(current_user=current_user, payload=payload, db=db)


@router.get(
    "/{id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    summary="Get product details by ID",
)
@router.get(
    "/{id}/",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_product(
    id: str,
    db: Session = Depends(get_db),
) -> ProductResponse:
    return ProductController.get_product(product_id=id, db=db)


@router.patch(
    "/{id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    summary="Update product (creator only)",
)
@router.patch(
    "/{id}/",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def update_product(
    id: str,
    payload: UpdateProductRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProductResponse:
    return ProductController.update_product(
        product_id=id,
        current_user=current_user,
        payload=payload,
        db=db,
    )


@router.delete(
    "/{id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete product (creator only)",
)
@router.delete(
    "/{id}/",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def delete_product(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    return ProductController.delete_product(
        product_id=id,
        current_user=current_user,
        db=db,
    )
