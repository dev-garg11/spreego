from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from src.models.user import User
from src.models.wallet import PayoutStatus, WalletTransactionType
from src.services.wallet_service import WalletService
from src.validations.wallet_schemas import (
    PayoutRequest,
    PayoutResponse,
    WalletResponse,
    WalletTransactionResponse,
)


class WalletController:
    @staticmethod
    def get_wallet(current_user: User, db: Session) -> WalletResponse:
        service = WalletService(db)
        try:
            return service.get_or_create_wallet(current_user)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))

    @staticmethod
    def get_wallet_by_id(wallet_id: str, current_user: User, db: Session) -> WalletResponse:
        service = WalletService(db)
        try:
            return service.get_wallet_by_id(wallet_id, current_user)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except PermissionError as err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))

    @staticmethod
    def get_transactions(
        current_user: User,
        transaction_type: Optional[WalletTransactionType],
        skip: int,
        limit: int,
        db: Session,
    ) -> List[WalletTransactionResponse]:
        service = WalletService(db)
        try:
            txns = service.get_transactions(
                current_user=current_user,
                transaction_type=transaction_type,
                skip=skip,
                limit=limit,
            )
            return [WalletTransactionResponse.model_validate(t) for t in txns]
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))

    @staticmethod
    def get_transaction_by_id(
        transaction_id: str, current_user: User, db: Session
    ) -> WalletTransactionResponse:
        service = WalletService(db)
        try:
            txn = service.get_transaction_by_id(transaction_id, current_user)
            return WalletTransactionResponse.model_validate(txn)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except PermissionError as err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))

    @staticmethod
    def request_payout(
        payload: PayoutRequest, current_user: User, db: Session
    ) -> PayoutResponse:
        service = WalletService(db)
        try:
            payout = service.request_payout(current_user=current_user, payload=payload)
            return PayoutResponse.model_validate(payout)
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except PermissionError as err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Database integrity constraint violation.",
            )

    @staticmethod
    def list_payouts(
        current_user: User,
        status_filter: Optional[PayoutStatus],
        skip: int,
        limit: int,
        db: Session,
    ) -> List[PayoutResponse]:
        service = WalletService(db)
        try:
            payouts = service.list_payouts(
                current_user=current_user,
                status=status_filter,
                skip=skip,
                limit=limit,
            )
            return [PayoutResponse.model_validate(p) for p in payouts]
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))

    @staticmethod
    def get_payout_by_id(
        payout_id: str, current_user: User, db: Session
    ) -> PayoutResponse:
        service = WalletService(db)
        try:
            payout = service.get_payout_by_id(payout_id, current_user)
            return PayoutResponse.model_validate(payout)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except PermissionError as err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))
