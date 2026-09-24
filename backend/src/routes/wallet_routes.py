from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.wallet_controller import WalletController
from src.middlewares.auth_middleware import get_current_user
from src.models.user import User
from src.models.wallet import PayoutStatus, WalletTransactionType
from src.validations.wallet_schemas import (
    PayoutRequest,
    PayoutResponse,
    WalletResponse,
    WalletTransactionResponse,
)

router = APIRouter(prefix="/api/v1/wallet", tags=["Wallet"])


@router.get(
    "",
    response_model=WalletResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current creator wallet details (auto-provisions if needed)",
)
@router.get(
    "/",
    response_model=WalletResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.get(
    "/me",
    response_model=WalletResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.get(
    "/me/",
    response_model=WalletResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_wallet(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WalletResponse:
    """Authenticated creator endpoint returning wallet details, active status,
    dynamically reconciled available balance, and pending payout balance.
    Auto-provisions a wallet if not exists."""
    return WalletController.get_wallet(current_user=current_user, db=db)


@router.get(
    "/transactions",
    response_model=List[WalletTransactionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get paginated immutable ledger transaction history",
)
@router.get(
    "/transactions/",
    response_model=List[WalletTransactionResponse],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.get(
    "/transaction",
    response_model=List[WalletTransactionResponse],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.get(
    "/transaction/",
    response_model=List[WalletTransactionResponse],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_transactions(
    type: Optional[WalletTransactionType] = Query(None, description="Filter by transaction type"),
    transaction_type: Optional[WalletTransactionType] = Query(
        None, description="Alias for filter by transaction type"
    ),
    page: Optional[int] = Query(None, ge=1, description="Page number (1-indexed)"),
    skip: Optional[int] = Query(None, ge=0, description="Offset"),
    limit: int = Query(50, ge=1, le=100, description="Page size limit"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[WalletTransactionResponse]:
    """Authenticated creator endpoint returning paginated immutable ledger transaction history."""
    offset = (page - 1) * limit if page is not None else (skip if skip is not None else 0)
    filter_type = type or transaction_type
    return WalletController.get_transactions(
        current_user=current_user,
        transaction_type=filter_type,
        skip=offset,
        limit=limit,
        db=db,
    )


@router.post(
    "/payout",
    response_model=PayoutResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request a withdrawal payout",
)
@router.post(
    "/payout/",
    response_model=PayoutResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
@router.post(
    "/payouts",
    response_model=PayoutResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
@router.post(
    "/payouts/",
    response_model=PayoutResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def request_payout(
    payload: PayoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PayoutResponse:
    """Authenticated creator endpoint to request a withdrawal payout.
    Validates requested amount > 0 and available balance >= requested amount.
    Atomically records payout and negative PAYOUT ledger transaction."""
    return WalletController.request_payout(
        payload=payload,
        current_user=current_user,
        db=db,
    )


@router.get(
    "/payouts",
    response_model=List[PayoutResponse],
    status_code=status.HTTP_200_OK,
    summary="List payout requests for current creator",
)
@router.get(
    "/payouts/",
    response_model=List[PayoutResponse],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.get(
    "/payout",
    response_model=List[PayoutResponse],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.get(
    "/payout/",
    response_model=List[PayoutResponse],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def list_payouts(
    status: Optional[PayoutStatus] = Query(None, description="Filter by payout status"),
    payout_status: Optional[PayoutStatus] = Query(
        None, description="Alias for filter by payout status"
    ),
    page: Optional[int] = Query(None, ge=1, description="Page number (1-indexed)"),
    skip: Optional[int] = Query(None, ge=0, description="Offset"),
    limit: int = Query(50, ge=1, le=100, description="Page size limit"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[PayoutResponse]:
    """Authenticated creator endpoint returning list of payout requests with statuses."""
    offset = (page - 1) * limit if page is not None else (skip if skip is not None else 0)
    filter_status = status or payout_status
    return WalletController.list_payouts(
        current_user=current_user,
        status_filter=filter_status,
        skip=offset,
        limit=limit,
        db=db,
    )


@router.get(
    "/payouts/{payout_id}",
    response_model=PayoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Get payout details (creator isolation enforced)",
)
@router.get(
    "/payouts/{payout_id}/",
    response_model=PayoutResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.get(
    "/payout/{payout_id}",
    response_model=PayoutResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.get(
    "/payout/{payout_id}/",
    response_model=PayoutResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_payout(
    payout_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PayoutResponse:
    """Authenticated endpoint to get payout details. Enforces isolation (403 for other creators)."""
    return WalletController.get_payout_by_id(
        payout_id=payout_id,
        current_user=current_user,
        db=db,
    )


@router.get(
    "/transactions/{transaction_id}",
    response_model=WalletTransactionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get transaction details (creator isolation enforced)",
)
@router.get(
    "/transactions/{transaction_id}/",
    response_model=WalletTransactionResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.get(
    "/transaction/{transaction_id}",
    response_model=WalletTransactionResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.get(
    "/transaction/{transaction_id}/",
    response_model=WalletTransactionResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_transaction(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WalletTransactionResponse:
    """Authenticated endpoint to get transaction details. Enforces isolation (403 for other creators)."""
    return WalletController.get_transaction_by_id(
        transaction_id=transaction_id,
        current_user=current_user,
        db=db,
    )


@router.get(
    "/{wallet_id}",
    response_model=WalletResponse,
    status_code=status.HTTP_200_OK,
    summary="Get wallet details by ID (creator isolation enforced)",
)
@router.get(
    "/{wallet_id}/",
    response_model=WalletResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_wallet_by_id(
    wallet_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WalletResponse:
    """Authenticated endpoint to get wallet by ID. Enforces isolation (403 for other creators)."""
    return WalletController.get_wallet_by_id(
        wallet_id=wallet_id,
        current_user=current_user,
        db=db,
    )
