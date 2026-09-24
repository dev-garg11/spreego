from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from src.models.wallet import (
    Payout,
    PayoutStatus,
    Wallet,
    WalletStatus,
    WalletTransaction,
    WalletTransactionType,
)
from src.repositories.base_repository import BaseRepository


class WalletRepository(BaseRepository[Wallet]):
    def __init__(self, db: Session):
        super().__init__(Wallet, db)

    def get_by_user_id(self, user_id: str) -> Optional[Wallet]:
        return self.db.query(Wallet).filter(Wallet.user_id == user_id).first()

    def get_or_create_wallet(self, user_id: str, currency: str = "INR") -> Wallet:
        wallet = self.get_by_user_id(user_id)
        if not wallet:
            try:
                wallet = Wallet(
                    user_id=user_id,
                    currency=currency,
                    status=WalletStatus.ACTIVE,
                )
                self.db.add(wallet)
                self.db.commit()
                self.db.refresh(wallet)
            except Exception:
                self.db.rollback()
                wallet = self.get_by_user_id(user_id)
        if wallet is None:
            raise LookupError(f"Failed to retrieve or provision wallet for user {user_id}")
        return wallet

    def get_ledger_balance(self, wallet_id: str) -> float:
        """Compute the sum of all immutable ledger transactions for this wallet."""
        total = (
            self.db.query(func.coalesce(func.sum(WalletTransaction.amount), 0.0))
            .filter(WalletTransaction.wallet_id == wallet_id)
            .scalar()
        )
        val = round(float(total), 2)
        return 0.0 if val == 0 else val

    def get_pending_payout_balance(self, wallet_id: str) -> float:
        """Compute total pending or processing payout balance."""
        total = (
            self.db.query(func.coalesce(func.sum(Payout.amount), 0.0))
            .filter(
                Payout.wallet_id == wallet_id,
                Payout.status.in_([PayoutStatus.PENDING, PayoutStatus.PROCESSING]),
            )
            .scalar()
        )
        val = round(float(total), 2)
        return 0.0 if val == 0 else val

    def get_available_balance(self, wallet_id: str) -> float:
        """Compute available withdrawable balance.
        If a pending payout already has a corresponding negative PAYOUT transaction
        in the ledger, its amount is already reflected in the ledger balance.
        Any unbooked pending payout is deducted from the ledger balance.
        """
        ledger_sum = self.get_ledger_balance(wallet_id)

        # Get reference_ids of PAYOUT transactions
        booked_payout_ids = {
            str(row[0])
            for row in self.db.query(WalletTransaction.reference_id)
            .filter(
                WalletTransaction.wallet_id == wallet_id,
                WalletTransaction.type == WalletTransactionType.PAYOUT,
                WalletTransaction.reference_id.isnot(None),
            )
            .all()
        }

        # Any pending payouts not yet booked in ledger
        pending_payouts = (
            self.db.query(Payout)
            .filter(
                Payout.wallet_id == wallet_id,
                Payout.status.in_([PayoutStatus.PENDING, PayoutStatus.PROCESSING]),
            )
            .all()
        )
        unbooked_amount = sum(
            (p.amount or 0.0) for p in pending_payouts if str(p.id) not in booked_payout_ids
        )
        val = round(float(ledger_sum - unbooked_amount), 2)
        return 0.0 if val == 0 else val

    def add_transaction(
        self,
        wallet_id: str,
        type: WalletTransactionType,
        amount: float,
        reference_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> WalletTransaction:
        rounded_amount = round(float(amount), 2)
        if rounded_amount == 0.0:
            raise ValueError("Transaction amount cannot be zero.")
        txn = WalletTransaction(
            wallet_id=wallet_id,
            type=type,
            amount=rounded_amount,
            reference_id=reference_id,
            description=description,
        )
        try:
            self.db.add(txn)
            self.db.commit()
            self.db.refresh(txn)
            return txn
        except Exception:
            self.db.rollback()
            raise

    def get_transactions(
        self,
        wallet_id: str,
        transaction_type: Optional[WalletTransactionType] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[WalletTransaction]:
        safe_skip = max(0, skip)
        safe_limit = max(1, min(limit, 100))
        query = self.db.query(WalletTransaction).filter(WalletTransaction.wallet_id == wallet_id)
        if transaction_type is not None:
            query = query.filter(WalletTransaction.type == transaction_type)
        return (
            query.order_by(WalletTransaction.created_at.desc())
            .offset(safe_skip)
            .limit(safe_limit)
            .all()
        )

    def get_transaction_by_id(self, transaction_id: str) -> Optional[WalletTransaction]:
        return (
            self.db.query(WalletTransaction)
            .filter(WalletTransaction.id == transaction_id)
            .first()
        )

    def create_payout(
        self,
        wallet_id: str,
        user_id: str,
        amount: float,
        payout_method: dict,
        status: PayoutStatus = PayoutStatus.PENDING,
    ) -> Payout:
        payout = Payout(
            wallet_id=wallet_id,
            user_id=user_id,
            amount=round(float(amount), 2),
            status=status,
            payout_method=payout_method,
        )
        try:
            self.db.add(payout)
            self.db.commit()
            self.db.refresh(payout)
            return payout
        except Exception:
            self.db.rollback()
            raise

    def get_payouts_by_user(
        self,
        user_id: str,
        status: Optional[PayoutStatus] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Payout]:
        safe_skip = max(0, skip)
        safe_limit = max(1, min(limit, 100))
        query = self.db.query(Payout).filter(Payout.user_id == user_id)
        if status is not None:
            query = query.filter(Payout.status == status)
        return (
            query.order_by(Payout.created_at.desc())
            .offset(safe_skip)
            .limit(safe_limit)
            .all()
        )

    def get_payout_by_id(self, payout_id: str) -> Optional[Payout]:
        return self.db.query(Payout).filter(Payout.id == payout_id).first()
