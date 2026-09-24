from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from src.models.user import User
from src.models.wallet import (
    Payout,
    PayoutStatus,
    Wallet,
    WalletStatus,
    WalletTransaction,
    WalletTransactionType,
)
from src.repositories.user_repository import UserRepository
from src.repositories.wallet_repository import WalletRepository
from src.validations.wallet_schemas import PayoutRequest, WalletResponse


class WalletService:
    def __init__(self, db: Session):
        self.db = db
        self.wallet_repo = WalletRepository(db)
        self.user_repo = UserRepository(db)

    def get_or_create_wallet(self, current_user: User) -> WalletResponse:
        """Fetch or auto-provision wallet for creator, returning reconciled balance."""
        wallet = self.wallet_repo.get_or_create_wallet(user_id=current_user.id)
        ledger_bal = self.wallet_repo.get_ledger_balance(wallet.id)
        avail = self.wallet_repo.get_available_balance(wallet.id)
        pending = self.wallet_repo.get_pending_payout_balance(wallet.id)
        return WalletResponse(
            id=wallet.id,
            user_id=wallet.user_id,
            currency=wallet.currency,
            status=wallet.status,
            is_active=(wallet.status == WalletStatus.ACTIVE),
            available_balance=avail,
            balance=ledger_bal,
            pending_payout_balance=pending,
            created_at=wallet.created_at,
            updated_at=wallet.updated_at,
        )

    def get_wallet_by_id(self, wallet_id: str, current_user: User) -> WalletResponse:
        """Fetch wallet by ID ensuring isolation and ownership."""
        wallet = self.wallet_repo.get_by_id(wallet_id)
        if not wallet:
            raise LookupError("Wallet not found.")
        if wallet.user_id != current_user.id:
            raise PermissionError("Access forbidden: You cannot access another creator's wallet.")
        ledger_bal = self.wallet_repo.get_ledger_balance(wallet.id)
        avail = self.wallet_repo.get_available_balance(wallet.id)
        pending = self.wallet_repo.get_pending_payout_balance(wallet.id)
        return WalletResponse(
            id=wallet.id,
            user_id=wallet.user_id,
            currency=wallet.currency,
            status=wallet.status,
            is_active=(wallet.status == WalletStatus.ACTIVE),
            available_balance=avail,
            balance=ledger_bal,
            pending_payout_balance=pending,
            created_at=wallet.created_at,
            updated_at=wallet.updated_at,
        )

    def get_transactions(
        self,
        current_user: User,
        transaction_type: Optional[WalletTransactionType] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[WalletTransaction]:
        """List paginated immutable transactions for current creator's wallet."""
        wallet = self.wallet_repo.get_or_create_wallet(user_id=current_user.id)
        return self.wallet_repo.get_transactions(
            wallet_id=wallet.id,
            transaction_type=transaction_type,
            skip=skip,
            limit=limit,
        )

    def get_transaction_by_id(
        self, transaction_id: str, current_user: User
    ) -> WalletTransaction:
        """Fetch a specific transaction with isolation check."""
        txn = self.wallet_repo.get_transaction_by_id(transaction_id)
        if not txn:
            raise LookupError("Transaction not found.")
        wallet = self.wallet_repo.get_by_id(txn.wallet_id)
        if not wallet:
            raise LookupError("Associated wallet not found.")
        if wallet.user_id != current_user.id:
            raise PermissionError("Access forbidden: You cannot access another creator's transaction.")
        return txn

    def request_payout(
        self,
        current_user: User,
        payload: PayoutRequest,
    ) -> Payout:
        """Request a payout withdrawal atomically deducting balance via negative ledger transaction."""
        amount = round(float(payload.amount), 2)
        if amount <= 0.0:
            raise ValueError("Payout amount must be greater than zero.")

        wallet = self.wallet_repo.get_or_create_wallet(user_id=current_user.id)
        if not wallet.is_active or wallet.status == WalletStatus.FROZEN:
            raise ValueError("Wallet is frozen or inactive. Cannot request payout.")

        # Row-level lock on wallet for concurrency protection on PostgreSQL
        try:
            bind = self.db.get_bind()
            if bind and bind.dialect.name == "postgresql":
                self.db.query(Wallet).filter(Wallet.id == wallet.id).with_for_update().first()
        except Exception:
            pass

        # Reconcile available balance
        avail = self.wallet_repo.get_available_balance(wallet.id)
        if avail < amount:
            raise ValueError(
                f"Insufficient Funds: Requested amount {amount:.2f} exceeds available balance {avail:.2f}."
            )

        # Atomic execution: create Payout and debit PAYOUT ledger transaction
        try:
            payout = Payout(
                wallet_id=wallet.id,
                user_id=current_user.id,
                amount=amount,
                status=PayoutStatus.PENDING,
                payout_method=payload.payout_method or {"upi_id": "creator@upi"},
            )
            self.db.add(payout)
            self.db.flush()

            txn = WalletTransaction(
                wallet_id=wallet.id,
                type=WalletTransactionType.PAYOUT,
                amount=-abs(amount),
                reference_id=payout.id,
                description=payload.description or f"Payout withdrawal request {payout.id}",
            )
            self.db.add(txn)
            self.db.commit()
            self.db.refresh(payout)
            return payout
        except Exception:
            self.db.rollback()
            raise

    def list_payouts(
        self,
        current_user: User,
        status: Optional[PayoutStatus] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Payout]:
        """List payout requests strictly isolated to current creator."""
        return self.wallet_repo.get_payouts_by_user(
            user_id=current_user.id,
            status=status,
            skip=skip,
            limit=limit,
        )

    def get_payout_by_id(
        self, payout_id: str, current_user: User
    ) -> Payout:
        """Get payout by ID ensuring creator isolation."""
        payout = self.wallet_repo.get_payout_by_id(payout_id)
        if not payout:
            raise LookupError("Payout not found.")
        if payout.user_id != current_user.id:
            raise PermissionError("Access forbidden: You cannot access another creator's payout.")
        return payout

    def add_earning(
        self,
        wallet_id: str,
        amount: float,
        reference_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> WalletTransaction:
        """Helper to record creator earnings or credits into the immutable ledger."""
        if amount <= 0.0:
            raise ValueError("Credit amount must be positive.")
        return self.wallet_repo.add_transaction(
            wallet_id=wallet_id,
            type=WalletTransactionType.CREATOR_EARNING,
            amount=amount,
            reference_id=reference_id,
            description=description,
        )

    def update_payout_status(
        self,
        payout_id: str,
        new_status: PayoutStatus,
        reason: Optional[str] = None,
    ) -> Payout:
        """Update payout lifecycle status. If REJECTED, automatically credit back ledger via ADJUSTMENT."""
        payout = self.wallet_repo.get_payout_by_id(payout_id)
        if not payout:
            raise LookupError(f"Payout {payout_id} not found.")

        old_status = payout.status
        if old_status in (PayoutStatus.COMPLETED, PayoutStatus.REJECTED):
            raise ValueError(f"Cannot update payout in terminal state {old_status}.")

        payout.status = new_status
        if new_status == PayoutStatus.REJECTED:
            # Recredit the debited amount to creator ledger
            self.wallet_repo.add_transaction(
                wallet_id=payout.wallet_id,
                type=WalletTransactionType.ADJUSTMENT,
                amount=abs(payout.amount),
                reference_id=payout.id,
                description=reason or f"Payout rejected - funds returned for {payout.id}",
            )
        else:
            self.db.commit()
            self.db.refresh(payout)
        return payout
