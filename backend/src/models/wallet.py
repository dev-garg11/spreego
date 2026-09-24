import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import backref, relationship
from src.config.database import Base


class WalletStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"


class WalletTransactionType(str, enum.Enum):
    CREATOR_EARNING = "CREATOR_EARNING"
    PLATFORM_FEE = "PLATFORM_FEE"
    REFUND = "REFUND"
    PAYOUT = "PAYOUT"
    ADJUSTMENT = "ADJUSTMENT"


# Alias TransactionType for convenience and backward compatibility
TransactionType = WalletTransactionType


class PayoutStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    currency = Column(String(10), default="INR", server_default="INR", nullable=False)
    status = Column(
        SAEnum(
            WalletStatus,
            name="wallet_status",
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=WalletStatus.ACTIVE,
        server_default=WalletStatus.ACTIVE.value,
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user = relationship(
        "User",
        backref=backref("wallet", uselist=False, cascade="all, delete-orphan", passive_deletes=True),
    )
    transactions = relationship(
        "WalletTransaction",
        back_populates="wallet",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    payouts = relationship(
        "Payout",
        back_populates="wallet",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Dynamic derived balance (anti-tampering: never stored as mutable scalar)
    @property
    def balance(self) -> float:
        """Dynamically derived balance reconciled from immutable ledger transactions."""
        if self.transactions:
            val = round(float(sum((t.amount or 0.0) for t in self.transactions)), 2)
            return 0.0 if val == 0 else val
        return 0.0

    @property
    def available_balance(self) -> float:
        """Reconciled available balance (ledger balance minus any unbooked pending payouts)."""
        ledger_bal = self.balance
        if not self.payouts:
            return ledger_bal
        booked_payout_ids = {
            str(t.reference_id)
            for t in (self.transactions or [])
            if t.type == WalletTransactionType.PAYOUT and t.reference_id
        }
        unbooked_amount = sum(
            (p.amount or 0.0)
            for p in self.payouts
            if p.status in (PayoutStatus.PENDING, PayoutStatus.PROCESSING)
            and str(p.id) not in booked_payout_ids
        )
        val = round(float(ledger_bal - unbooked_amount), 2)
        return 0.0 if val == 0 else val

    @property
    def pending_payout_balance(self) -> float:
        """Dynamically derived total of pending and processing payouts."""
        if self.payouts:
            val = round(
                float(
                    sum(
                        (p.amount or 0.0)
                        for p in self.payouts
                        if p.status in (PayoutStatus.PENDING, PayoutStatus.PROCESSING)
                    )
                ),
                2,
            )
            return 0.0 if val == 0 else val
        return 0.0

    @property
    def is_active(self) -> bool:
        return self.status == WalletStatus.ACTIVE

    def __repr__(self) -> str:
        return f"<Wallet(id='{self.id}', user_id='{self.user_id}', currency='{self.currency}', status='{self.status}')>"


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    wallet_id = Column(
        String(36),
        ForeignKey("wallets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type = Column(
        SAEnum(
            WalletTransactionType,
            name="wallet_transaction_type",
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        index=True,
    )
    amount = Column(Float, nullable=False)
    reference_id = Column(String(255), nullable=True, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    wallet = relationship("Wallet", back_populates="transactions")

    def __repr__(self) -> str:
        return f"<WalletTransaction(id='{self.id}', wallet_id='{self.wallet_id}', type='{self.type}', amount={self.amount})>"


class Payout(Base):
    __tablename__ = "payouts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    wallet_id = Column(
        String(36),
        ForeignKey("wallets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount = Column(Float, nullable=False)
    status = Column(
        SAEnum(
            PayoutStatus,
            name="payout_status",
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=PayoutStatus.PENDING,
        server_default=PayoutStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    payout_method = Column(JSON, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    wallet = relationship("Wallet", back_populates="payouts")
    user = relationship(
        "User",
        backref=backref("payouts", cascade="all, delete-orphan", passive_deletes=True),
    )

    def __repr__(self) -> str:
        return f"<Payout(id='{self.id}', wallet_id='{self.wallet_id}', user_id='{self.user_id}', amount={self.amount}, status='{self.status}')>"
