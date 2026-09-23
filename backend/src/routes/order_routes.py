from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.order_controller import OrderController
from src.middlewares.auth_middleware import get_current_user
from src.models.user import User
from src.validations.commerce_schemas import (
    CreateOrderRequest,
    OrderResponse,
    UpdateOrderStatusRequest,
)

router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Place a new order (authenticated buyer)",
)
@router.post(
    "/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_order(
    payload: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrderResponse:
    """Authenticated buyer endpoint to place an order.
    Total amount is computed server-side; inventory is decremented for physical items."""
    return OrderController.create_order(current_user=current_user, payload=payload, db=db)


@router.get(
    "/my",
    response_model=List[OrderResponse],
    status_code=status.HTTP_200_OK,
    summary="List orders placed by current user",
)
@router.get(
    "/my/",
    response_model=List[OrderResponse],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_my_orders(
    page: Optional[int] = Query(None, ge=1, description="Page number (1-indexed)"),
    skip: Optional[int] = Query(None, ge=0, description="Offset"),
    limit: int = Query(50, ge=1, le=100, description="Page size limit"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[OrderResponse]:
    """Authenticated endpoint returning list of orders placed by the current user."""
    offset = (page - 1) * limit if page is not None else (skip if skip is not None else 0)
    return OrderController.get_my_orders(current_user=current_user, skip=offset, limit=limit, db=db)


@router.get(
    "",
    response_model=List[OrderResponse],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.get(
    "/",
    response_model=List[OrderResponse],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def list_orders_alias(
    page: Optional[int] = Query(None, ge=1, description="Page number (1-indexed)"),
    skip: Optional[int] = Query(None, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[OrderResponse]:
    """Fallback alias returning current user's orders."""
    offset = (page - 1) * limit if page is not None else (skip if skip is not None else 0)
    return OrderController.get_my_orders(current_user=current_user, skip=offset, limit=limit, db=db)


@router.get(
    "/store",
    response_model=List[OrderResponse],
    status_code=status.HTTP_200_OK,
    summary="List orders received by current user (as store owner/seller)",
)
@router.get(
    "/store/",
    response_model=List[OrderResponse],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_store_orders(
    page: Optional[int] = Query(None, ge=1, description="Page number (1-indexed)"),
    skip: Optional[int] = Query(None, ge=0, description="Offset"),
    limit: int = Query(50, ge=1, le=100, description="Page size limit"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[OrderResponse]:
    """Authenticated endpoint returning list of orders placed for the current seller's store."""
    offset = (page - 1) * limit if page is not None else (skip if skip is not None else 0)
    return OrderController.get_store_orders(current_user=current_user, skip=offset, limit=limit, db=db)


@router.get(
    "/{id}",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
    summary="View order details (buyer or seller only)",
)
@router.get(
    "/{id}/",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_order(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrderResponse:
    """Authenticated endpoint to view order details. Accessible only to buyer or seller."""
    return OrderController.get_order(order_id=id, current_user=current_user, db=db)


@router.post(
    "/{id}/cancel",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel order (buyer or seller; restores inventory)",
)
@router.post(
    "/{id}/cancel/",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def cancel_order(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrderResponse:
    """Authenticated endpoint to cancel an order. Re-credits inventory if cancelled before shipping."""
    return OrderController.cancel_order(order_id=id, current_user=current_user, db=db)


@router.patch(
    "/{id}/status",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Update order status (seller only)",
)
@router.patch(
    "/{id}/status/",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def update_order_status(
    id: str,
    payload: UpdateOrderStatusRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrderResponse:
    """Authenticated endpoint for seller to update order status (e.g. PROCESSING, SHIPPED, DELIVERED)."""
    return OrderController.update_order_status(
        order_id=id,
        current_user=current_user,
        payload=payload,
        db=db,
    )
