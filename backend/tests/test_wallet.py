import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.config.database import Base
from src.config.security import create_access_token
from src.models.profile import Profile
from src.models.user import User
from src.models.wallet import (
    Payout,
    PayoutStatus,
    TransactionType,
    Wallet,
    WalletStatus,
    WalletTransaction,
    WalletTransactionType,
)
from src.repositories.wallet_repository import WalletRepository
from src.services.wallet_service import WalletService
from src.validations.wallet_schemas import PayoutRequest


# ============================================================================
# Helpers
# ============================================================================

def create_test_user(
    db: Session,
    phone_number: str = None,
    email: str = None,
    username: str = None,
    is_active: bool = True,
) -> User:
    """Helper to provision a test user with profile directly into test DB."""
    uid = str(uuid.uuid4())[:8]
    phone = phone_number or f"+9197{uid[:6]}"
    mail = email or f"creator_{uid}@spreego.com"
    handle = username or f"creator_{uid}"

    user = User(
        phone_number=phone,
        email=mail,
        is_active=is_active,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    profile = Profile(
        user_id=user.id,
        username=handle,
        full_name=f"Creator {handle}",
    )
    db.add(profile)
    db.commit()
    db.refresh(user)
    return user


def auth_headers(user_id: str) -> dict:
    """Helper to generate Authorization header for user_id."""
    token = create_access_token(user_id=user_id)
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# 1. Database & Metadata Verification (Banking-Standard Immutable Ledger)
# ============================================================================

def test_wallet_models_registered_in_base_metadata():
    """Verify wallets, wallet_transactions, and payouts tables are in Base metadata."""
    assert "wallets" in Base.metadata.tables
    assert "wallet_transactions" in Base.metadata.tables
    assert "payouts" in Base.metadata.tables

    wallet_table = Base.metadata.tables["wallets"]
    assert "id" in wallet_table.columns
    assert "user_id" in wallet_table.columns
    assert "currency" in wallet_table.columns
    assert "status" in wallet_table.columns
    assert "created_at" in wallet_table.columns
    assert "updated_at" in wallet_table.columns

    # CRITICAL: Verify NO mutable 'balance' scalar column exists on wallets table
    assert "balance" not in wallet_table.columns
    assert "available_balance" not in wallet_table.columns

    tx_table = Base.metadata.tables["wallet_transactions"]
    assert "id" in tx_table.columns
    assert "wallet_id" in tx_table.columns
    assert "type" in tx_table.columns
    assert "amount" in tx_table.columns
    assert "reference_id" in tx_table.columns
    assert "description" in tx_table.columns
    assert "created_at" in tx_table.columns
    # Immutable ledger records must NOT have an updated_at column
    assert "updated_at" not in tx_table.columns

    payout_table = Base.metadata.tables["payouts"]
    assert "id" in payout_table.columns
    assert "wallet_id" in payout_table.columns
    assert "user_id" in payout_table.columns
    assert "amount" in payout_table.columns
    assert "status" in payout_table.columns
    assert "payout_method" in payout_table.columns
    assert "created_at" in payout_table.columns
    assert "updated_at" in payout_table.columns


def test_wallet_direct_model_instantiation(db_session: Session):
    """Direct model instantiation and relationship checks in database."""
    creator = create_test_user(db_session, username="direct_wallet_user")

    wallet = Wallet(
        user_id=creator.id,
        currency="INR",
        status=WalletStatus.ACTIVE,
    )
    db_session.add(wallet)
    db_session.commit()
    db_session.refresh(wallet)

    assert wallet.id is not None
    assert wallet.currency == "INR"
    assert wallet.status == WalletStatus.ACTIVE
    assert wallet.is_active is True
    assert wallet.balance == 0.0
    assert wallet.available_balance == 0.0
    assert wallet.pending_payout_balance == 0.0
    assert wallet.user.id == creator.id

    # Add ledger transaction
    txn = WalletTransaction(
        wallet_id=wallet.id,
        type=WalletTransactionType.CREATOR_EARNING,
        amount=500.0,
        reference_id="order_123",
        description="Sale earning",
    )
    db_session.add(txn)
    db_session.commit()
    db_session.refresh(wallet)

    assert len(wallet.transactions) == 1
    assert wallet.balance == 500.0
    assert wallet.available_balance == 500.0

    # Add payout
    payout = Payout(
        wallet_id=wallet.id,
        user_id=creator.id,
        amount=150.0,
        status=PayoutStatus.PENDING,
        payout_method={"upi_id": "creator@upi"},
    )
    db_session.add(payout)
    db_session.commit()
    db_session.refresh(wallet)

    assert len(wallet.payouts) == 1
    assert wallet.pending_payout_balance == 150.0


# ============================================================================
# 2. Automatic Wallet Provisioning (GET /api/v1/wallet)
# ============================================================================

def test_get_wallet_auto_provisions_new_wallet(client: TestClient, db_session: Session):
    """First access by an authenticated creator automatically provisions a wallet."""
    creator = create_test_user(db_session, username="auto_wallet_1")
    headers = auth_headers(creator.id)

    # Pre-check: user has no wallet
    existing_wallet = db_session.query(Wallet).filter(Wallet.user_id == creator.id).first()
    assert existing_wallet is None

    # Call endpoint
    resp = client.get("/api/v1/wallet", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["id"] is not None
    assert data["user_id"] == creator.id
    assert data["currency"] == "INR"
    assert data["status"] == "ACTIVE"
    assert data["is_active"] is True
    assert data["available_balance"] == 0.0
    assert data["balance"] == 0.0
    assert data["pending_payout_balance"] == 0.0

    # Verify wallet now exists in database
    db_wallet = db_session.query(Wallet).filter(Wallet.user_id == creator.id).first()
    assert db_wallet is not None
    assert db_wallet.id == data["id"]


def test_auto_provision_idempotency(client: TestClient, db_session: Session):
    """Subsequent requests return existing wallet without creating duplicate wallets."""
    creator = create_test_user(db_session, username="auto_wallet_idemp")
    headers = auth_headers(creator.id)

    resp1 = client.get("/api/v1/wallet", headers=headers)
    assert resp1.status_code == 200
    id1 = resp1.json()["id"]

    resp2 = client.get("/api/v1/wallet/", headers=headers)
    assert resp2.status_code == 200
    id2 = resp2.json()["id"]

    assert id1 == id2
    wallets_count = db_session.query(Wallet).filter(Wallet.user_id == creator.id).count()
    assert wallets_count == 1


# ============================================================================
# 3. Dynamic Balance Calculation & Anti-Tampering (Ledger Reconciliation)
# ============================================================================

def test_dynamic_balance_calculation_credits_and_debits(client: TestClient, db_session: Session):
    """Verify balance is dynamically computed from credits and debits in immutable ledger."""
    creator = create_test_user(db_session, username="ledger_calc_user")
    headers = auth_headers(creator.id)

    # Initial balance is 0.0
    resp = client.get("/api/v1/wallet", headers=headers)
    assert resp.status_code == 200
    wallet_id = resp.json()["id"]
    assert resp.json()["available_balance"] == 0.0

    # Inject credits and debits into ledger
    t1 = WalletTransaction(
        wallet_id=wallet_id,
        type=WalletTransactionType.CREATOR_EARNING,
        amount=1000.0,
        description="Sale 1",
    )
    t2 = WalletTransaction(
        wallet_id=wallet_id,
        type=WalletTransactionType.CREATOR_EARNING,
        amount=500.0,
        description="Sale 2",
    )
    t3 = WalletTransaction(
        wallet_id=wallet_id,
        type=WalletTransactionType.PLATFORM_FEE,
        amount=-150.0,
        description="Platform fee 10%",
    )
    t4 = WalletTransaction(
        wallet_id=wallet_id,
        type=WalletTransactionType.REFUND,
        amount=-50.0,
        description="Customer refund",
    )
    t5 = WalletTransaction(
        wallet_id=wallet_id,
        type=WalletTransactionType.ADJUSTMENT,
        amount=25.0,
        description="Bonus credit",
    )
    db_session.add_all([t1, t2, t3, t4, t5])
    db_session.commit()

    # Reconciled balance: 1000 + 500 - 150 - 50 + 25 = 1325.0
    resp_reconciled = client.get("/api/v1/wallet", headers=headers)
    assert resp_reconciled.status_code == 200
    data = resp_reconciled.json()
    assert data["available_balance"] == 1325.0
    assert data["balance"] == 1325.0


def test_anti_tampering_direct_ledger_reflection(client: TestClient, db_session: Session):
    """Verify that ledger tampering is impossible: balance reflects ledger rows in real-time."""
    creator = create_test_user(db_session, username="tamper_test_user")
    headers = auth_headers(creator.id)

    client.get("/api/v1/wallet", headers=headers)
    wallet = db_session.query(Wallet).filter(Wallet.user_id == creator.id).one()

    # Add transaction
    txn = WalletTransaction(
        wallet_id=wallet.id,
        type=WalletTransactionType.CREATOR_EARNING,
        amount=750.50,
    )
    db_session.add(txn)
    db_session.commit()

    resp = client.get("/api/v1/wallet", headers=headers)
    assert resp.json()["available_balance"] == 750.50

    # Add a debit transaction
    debit = WalletTransaction(
        wallet_id=wallet.id,
        type=WalletTransactionType.PAYOUT,
        amount=-250.50,
    )
    db_session.add(debit)
    db_session.commit()

    resp_after_debit = client.get("/api/v1/wallet", headers=headers)
    assert resp_after_debit.json()["available_balance"] == 500.0


# ============================================================================
# 4. Transaction History & Filtering & Pagination (GET /api/v1/wallet/transactions)
# ============================================================================

def test_get_transactions_empty(client: TestClient, db_session: Session):
    """Newly provisioned wallet returns empty transaction list."""
    creator = create_test_user(db_session, username="tx_empty_user")
    headers = auth_headers(creator.id)

    resp = client.get("/api/v1/wallet/transactions", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_transactions_filtering_by_type(client: TestClient, db_session: Session):
    """Filter immutable transactions by type."""
    creator = create_test_user(db_session, username="tx_filter_user")
    headers = auth_headers(creator.id)

    client.get("/api/v1/wallet", headers=headers)
    wallet = db_session.query(Wallet).filter(Wallet.user_id == creator.id).one()

    t1 = WalletTransaction(wallet_id=wallet.id, type=WalletTransactionType.CREATOR_EARNING, amount=100.0)
    t2 = WalletTransaction(wallet_id=wallet.id, type=WalletTransactionType.CREATOR_EARNING, amount=200.0)
    t3 = WalletTransaction(wallet_id=wallet.id, type=WalletTransactionType.PLATFORM_FEE, amount=-30.0)
    t4 = WalletTransaction(wallet_id=wallet.id, type=WalletTransactionType.REFUND, amount=-20.0)
    db_session.add_all([t1, t2, t3, t4])
    db_session.commit()

    # Filter by CREATOR_EARNING
    resp_earning = client.get("/api/v1/wallet/transactions?type=CREATOR_EARNING", headers=headers)
    assert resp_earning.status_code == 200
    earnings = resp_earning.json()
    assert len(earnings) == 2
    assert all(t["type"] == "CREATOR_EARNING" for t in earnings)

    # Filter by PLATFORM_FEE
    resp_fee = client.get("/api/v1/wallet/transactions?type=PLATFORM_FEE", headers=headers)
    assert resp_fee.status_code == 200
    fees = resp_fee.json()
    assert len(fees) == 1
    assert fees[0]["amount"] == -30.0

    # Filter by alias transaction_type
    resp_alias = client.get("/api/v1/wallet/transactions?transaction_type=REFUND", headers=headers)
    assert resp_alias.status_code == 200
    refunds = resp_alias.json()
    assert len(refunds) == 1
    assert refunds[0]["type"] == "REFUND"


def test_get_transactions_pagination(client: TestClient, db_session: Session):
    """Paginate immutable transaction history with limit and offset."""
    creator = create_test_user(db_session, username="tx_page_user")
    headers = auth_headers(creator.id)

    client.get("/api/v1/wallet", headers=headers)
    wallet = db_session.query(Wallet).filter(Wallet.user_id == creator.id).one()

    # Add 5 transactions
    for i in range(1, 6):
        db_session.add(
            WalletTransaction(
                wallet_id=wallet.id,
                type=WalletTransactionType.CREATOR_EARNING,
                amount=float(i * 10),
                description=f"Tx {i}",
            )
        )
    db_session.commit()

    # Limit 2
    resp_l2 = client.get("/api/v1/wallet/transactions?limit=2", headers=headers)
    assert resp_l2.status_code == 200
    assert len(resp_l2.json()) == 2

    # Page 2 with limit 2
    resp_p2 = client.get("/api/v1/wallet/transactions?page=2&limit=2", headers=headers)
    assert resp_p2.status_code == 200
    assert len(resp_p2.json()) == 2

    # Page 3 with limit 2 (last remaining 1)
    resp_p3 = client.get("/api/v1/wallet/transactions?page=3&limit=2", headers=headers)
    assert resp_p3.status_code == 200
    assert len(resp_p3.json()) == 1


# ============================================================================
# 5. Payout Request Validation & Rejection (POST /api/v1/wallet/payout)
# ============================================================================

def test_payout_rejection_negative_or_zero_amount(client: TestClient, db_session: Session):
    """Rejection of negative or zero payout amounts returns HTTP 400 or 422."""
    creator = create_test_user(db_session, username="val_payout_user")
    headers = auth_headers(creator.id)

    # Zero amount
    resp_zero = client.post("/api/v1/wallet/payout", json={"amount": 0.0}, headers=headers)
    assert resp_zero.status_code in (400, 422)

    # Negative amount
    resp_neg = client.post("/api/v1/wallet/payout", json={"amount": -50.0}, headers=headers)
    assert resp_neg.status_code in (400, 422)

    # Missing amount
    resp_missing = client.post("/api/v1/wallet/payout", json={}, headers=headers)
    assert resp_missing.status_code == 422


def test_payout_rejection_insufficient_funds(client: TestClient, db_session: Session):
    """Rejection of payout requests exceeding available balance with HTTP 400 Insufficient Funds."""
    creator = create_test_user(db_session, username="insufficient_user")
    headers = auth_headers(creator.id)

    # User has 0 balance
    resp_0 = client.post(
        "/api/v1/wallet/payout",
        json={"amount": 100.0, "payout_method": {"upi_id": "creator@upi"}},
        headers=headers,
    )
    assert resp_0.status_code == 400
    assert "insufficient" in resp_0.json()["detail"].lower()

    # Provision wallet with 300 balance
    client.get("/api/v1/wallet", headers=headers)
    wallet = db_session.query(Wallet).filter(Wallet.user_id == creator.id).one()
    db_session.add(
        WalletTransaction(
            wallet_id=wallet.id,
            type=WalletTransactionType.CREATOR_EARNING,
            amount=300.0,
        )
    )
    db_session.commit()

    # Request 300.01 (exceeds available 300.0)
    resp_exceed = client.post(
        "/api/v1/wallet/payout",
        json={"amount": 300.01, "payout_method": {"upi_id": "creator@upi"}},
        headers=headers,
    )
    assert resp_exceed.status_code == 400
    assert "insufficient" in resp_exceed.json()["detail"].lower()


def test_payout_rejection_frozen_wallet(client: TestClient, db_session: Session):
    """Rejection of payout requests when creator wallet is FROZEN."""
    creator = create_test_user(db_session, username="frozen_user")
    headers = auth_headers(creator.id)

    client.get("/api/v1/wallet", headers=headers)
    wallet = db_session.query(Wallet).filter(Wallet.user_id == creator.id).one()
    wallet.status = WalletStatus.FROZEN
    db_session.add(
        WalletTransaction(
            wallet_id=wallet.id,
            type=WalletTransactionType.CREATOR_EARNING,
            amount=1000.0,
        )
    )
    db_session.commit()

    resp = client.post(
        "/api/v1/wallet/payout",
        json={"amount": 100.0},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "frozen" in resp.json()["detail"].lower()


# ============================================================================
# 6. Successful Payout & Atomic Ledger Deduction
# ============================================================================

def test_successful_payout_atomic_deduction(client: TestClient, db_session: Session):
    """Creator requests payout; ledger transaction is atomically recorded with negative amount."""
    creator = create_test_user(db_session, username="payout_success_user")
    headers = auth_headers(creator.id)

    # Fund creator wallet with 1000 INR
    client.get("/api/v1/wallet", headers=headers)
    wallet = db_session.query(Wallet).filter(Wallet.user_id == creator.id).one()
    db_session.add(
        WalletTransaction(
            wallet_id=wallet.id,
            type=WalletTransactionType.CREATOR_EARNING,
            amount=1000.0,
            description="Initial earnings",
        )
    )
    db_session.commit()

    # Request 400 INR payout
    payload = {
        "amount": 400.0,
        "payout_method": {"upi_id": "creator@okaxis", "name": "Creator Name"},
        "description": "Weekly withdrawal",
    }
    resp = client.post("/api/v1/wallet/payout", json=payload, headers=headers)
    assert resp.status_code == 201
    payout_data = resp.json()
    assert payout_data["id"] is not None
    assert payout_data["amount"] == 400.0
    assert payout_data["status"] == "PENDING"
    assert payout_data["payout_method"]["upi_id"] == "creator@okaxis"

    # Verify that a negative PAYOUT transaction was committed atomically
    debit_tx = (
        db_session.query(WalletTransaction)
        .filter(
            WalletTransaction.wallet_id == wallet.id,
            WalletTransaction.type == WalletTransactionType.PAYOUT,
            WalletTransaction.reference_id == payout_data["id"],
        )
        .first()
    )
    assert debit_tx is not None
    assert debit_tx.amount == -400.0

    # Verify new wallet state: available balance is now 600, pending payout is 400
    resp_wallet = client.get("/api/v1/wallet", headers=headers)
    assert resp_wallet.status_code == 200
    w_data = resp_wallet.json()
    assert w_data["available_balance"] == 600.0
    assert w_data["balance"] == 600.0
    assert w_data["pending_payout_balance"] == 400.0

    # Subsequent request for 700 exceeds remaining 600 -> rejected
    resp_reject = client.post("/api/v1/wallet/payout", json={"amount": 700.0}, headers=headers)
    assert resp_reject.status_code == 400
    assert "insufficient" in resp_reject.json()["detail"].lower()

    # Subsequent request for remaining 600 succeeds
    resp_drain = client.post("/api/v1/wallet/payout", json={"amount": 600.0}, headers=headers)
    assert resp_drain.status_code == 201

    resp_empty = client.get("/api/v1/wallet", headers=headers)
    assert resp_empty.json()["available_balance"] == 0.0
    assert resp_empty.json()["pending_payout_balance"] == 1000.0


# ============================================================================
# 7. Payout Requests Listing & History (GET /api/v1/wallet/payouts)
# ============================================================================

def test_list_payouts_for_creator(client: TestClient, db_session: Session):
    """Creator can list all their payout requests and filter by status."""
    creator = create_test_user(db_session, username="list_payouts_user")
    headers = auth_headers(creator.id)

    # Fund creator
    client.get("/api/v1/wallet", headers=headers)
    wallet = db_session.query(Wallet).filter(Wallet.user_id == creator.id).one()
    db_session.add(
        WalletTransaction(wallet_id=wallet.id, type=WalletTransactionType.CREATOR_EARNING, amount=2000.0)
    )
    db_session.commit()

    # Create 2 payouts
    client.post("/api/v1/wallet/payout", json={"amount": 300.0}, headers=headers)
    client.post("/api/v1/wallet/payout", json={"amount": 500.0}, headers=headers)

    # List payouts
    resp = client.get("/api/v1/wallet/payouts", headers=headers)
    assert resp.status_code == 200
    payouts = resp.json()
    assert len(payouts) == 2
    assert payouts[0]["user_id"] == creator.id
    assert payouts[1]["user_id"] == creator.id

    # Filter by status PENDING
    resp_filter = client.get("/api/v1/wallet/payouts?status=PENDING", headers=headers)
    assert resp_filter.status_code == 200
    assert len(resp_filter.json()) == 2

    # Filter by COMPLETED (none yet)
    resp_empty = client.get("/api/v1/wallet/payouts?status=COMPLETED", headers=headers)
    assert resp_empty.status_code == 200
    assert len(resp_empty.json()) == 0


# ============================================================================
# 8. Creator Isolation & Security (HTTP 403 / Isolated Queries)
# ============================================================================

def test_creator_isolation_endpoints(client: TestClient, db_session: Session):
    """Creator A cannot access Creator B's wallet, transactions, or payouts."""
    creator_a = create_test_user(db_session, username="creator_alpha")
    creator_b = create_test_user(db_session, username="creator_beta")

    headers_a = auth_headers(creator_a.id)
    headers_b = auth_headers(creator_b.id)

    # Provision both
    resp_a = client.get("/api/v1/wallet", headers=headers_a)
    wallet_a_id = resp_a.json()["id"]

    resp_b = client.get("/api/v1/wallet", headers=headers_b)
    wallet_b_id = resp_b.json()["id"]

    assert wallet_a_id != wallet_b_id

    # Fund Creator B
    db_session.add(
        WalletTransaction(
            wallet_id=wallet_b_id,
            type=WalletTransactionType.CREATOR_EARNING,
            amount=5000.0,
            description="Creator B secret earnings",
        )
    )
    db_session.commit()

    # Creator B creates a payout
    resp_payout_b = client.post(
        "/api/v1/wallet/payout",
        json={"amount": 1000.0, "payout_method": {"upi_id": "creator_b@upi"}},
        headers=headers_b,
    )
    payout_b_id = resp_payout_b.json()["id"]

    # 1. Creator A attempts to fetch Creator B's wallet by ID -> 403 Forbidden
    resp_hack_wallet = client.get(f"/api/v1/wallet/{wallet_b_id}", headers=headers_a)
    assert resp_hack_wallet.status_code == 403

    # 2. Creator A lists transactions -> sees 0 transactions (Creator B's 5000 earnings never leaked)
    resp_tx_a = client.get("/api/v1/wallet/transactions", headers=headers_a)
    assert resp_tx_a.status_code == 200
    assert len(resp_tx_a.json()) == 0

    # 3. Creator A lists payouts -> sees 0 payouts (Creator B's payout never leaked)
    resp_po_a = client.get("/api/v1/wallet/payouts", headers=headers_a)
    assert resp_po_a.status_code == 200
    assert len(resp_po_a.json()) == 0

    # 4. Creator A attempts to fetch Creator B's payout by ID -> 403 Forbidden
    resp_hack_payout = client.get(f"/api/v1/wallet/payouts/{payout_b_id}", headers=headers_a)
    assert resp_hack_payout.status_code == 403

    # 5. Creator A attempts to fetch Creator B's transaction by ID -> 403 Forbidden
    tx_b = db_session.query(WalletTransaction).filter(WalletTransaction.wallet_id == wallet_b_id).first()
    assert tx_b is not None
    resp_hack_tx = client.get(f"/api/v1/wallet/transactions/{tx_b.id}", headers=headers_a)
    assert resp_hack_tx.status_code == 403


# ============================================================================
# 9. Authentication Security (HTTP 401 on unauthenticated access)
# ============================================================================

def test_wallet_endpoints_require_authentication(client: TestClient):
    """All creator wallet endpoints require valid Bearer token."""
    assert client.get("/api/v1/wallet").status_code == 401
    assert client.get("/api/v1/wallet/transactions").status_code == 401
    assert client.post("/api/v1/wallet/payout", json={"amount": 100}).status_code == 401
    assert client.get("/api/v1/wallet/payouts").status_code == 401
    assert client.get("/api/v1/wallet/some-id").status_code == 401
    assert client.get("/api/v1/wallet/payouts/some-id").status_code == 401
    assert client.get("/api/v1/wallet/transactions/some-id").status_code == 401


# ============================================================================
# 10. Payout Lifecycle: Processing, Completed, and Rejected
# ============================================================================

def test_payout_completed_lifecycle(client: TestClient, db_session: Session):
    """When a payout transitions to COMPLETED, pending_payout_balance drops to 0."""
    creator = create_test_user(db_session, username="lifecycle_comp_user")
    headers = auth_headers(creator.id)

    # Fund creator with 1000
    client.get("/api/v1/wallet", headers=headers)
    wallet = db_session.query(Wallet).filter(Wallet.user_id == creator.id).one()
    db_session.add(
        WalletTransaction(wallet_id=wallet.id, type=WalletTransactionType.CREATOR_EARNING, amount=1000.0)
    )
    db_session.commit()

    # Request 350 payout
    resp_po = client.post("/api/v1/wallet/payout", json={"amount": 350.0}, headers=headers)
    assert resp_po.status_code == 201
    payout_id = resp_po.json()["id"]

    # Verify pending state
    resp1 = client.get("/api/v1/wallet", headers=headers)
    assert resp1.json()["available_balance"] == 650.0
    assert resp1.json()["pending_payout_balance"] == 350.0

    # Mark payout as COMPLETED
    payout = db_session.query(Payout).filter(Payout.id == payout_id).one()
    payout.status = PayoutStatus.COMPLETED
    db_session.commit()

    # Available balance stays 650, pending payout drops to 0
    resp2 = client.get("/api/v1/wallet", headers=headers)
    assert resp2.json()["available_balance"] == 650.0
    assert resp2.json()["pending_payout_balance"] == 0.0


def test_payout_rejected_lifecycle_with_refund(client: TestClient, db_session: Session):
    """When a payout is rejected, an adjustment credit restores available balance."""
    creator = create_test_user(db_session, username="lifecycle_rej_user")
    headers = auth_headers(creator.id)

    client.get("/api/v1/wallet", headers=headers)
    wallet = db_session.query(Wallet).filter(Wallet.user_id == creator.id).one()
    db_session.add(
        WalletTransaction(wallet_id=wallet.id, type=WalletTransactionType.CREATOR_EARNING, amount=500.0)
    )
    db_session.commit()

    # Request 200 payout
    resp_po = client.post("/api/v1/wallet/payout", json={"amount": 200.0}, headers=headers)
    payout_id = resp_po.json()["id"]

    # Mark payout as REJECTED and post compensating ledger adjustment
    payout = db_session.query(Payout).filter(Payout.id == payout_id).one()
    payout.status = PayoutStatus.REJECTED
    db_session.add(
        WalletTransaction(
            wallet_id=wallet.id,
            type=WalletTransactionType.ADJUSTMENT,
            amount=200.0,
            reference_id=payout.id,
            description="Payout rejected - funds returned",
        )
    )
    db_session.commit()

    # Reconciled balance restored to 500, pending is 0
    resp = client.get("/api/v1/wallet", headers=headers)
    assert resp.json()["available_balance"] == 500.0
    assert resp.json()["pending_payout_balance"] == 0.0


# ============================================================================
# 11. Bank Account Details & Custom Payout Methods
# ============================================================================

def test_payout_with_bank_account_details(client: TestClient, db_session: Session):
    """Creator can request payout using bank account credentials in payout_method JSON."""
    creator = create_test_user(db_session, username="bank_payout_user")
    headers = auth_headers(creator.id)

    client.get("/api/v1/wallet", headers=headers)
    wallet = db_session.query(Wallet).filter(Wallet.user_id == creator.id).one()
    db_session.add(
        WalletTransaction(wallet_id=wallet.id, type=WalletTransactionType.CREATOR_EARNING, amount=2000.0)
    )
    db_session.commit()

    bank_details = {
        "account_holder": "Creator Alpha",
        "bank_name": "State Bank of India",
        "account_number": "123456789012",
        "ifsc_code": "SBIN0001234",
    }
    payload = {
        "amount": 1250.0,
        "payout_method": bank_details,
        "description": "NEFT transfer to SBI",
    }
    resp = client.post("/api/v1/wallet/payout", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["amount"] == 1250.0
    assert data["payout_method"]["account_number"] == "123456789012"
    assert data["payout_method"]["ifsc_code"] == "SBIN0001234"


# ============================================================================
# 12. Direct Service Error Paths & Boundary Values
# ============================================================================

def test_wallet_service_direct_exceptions(db_session: Session):
    """Test WalletService methods handle exceptions and validation properly."""
    service = WalletService(db_session)
    creator = create_test_user(db_session, username="svc_user_1")
    other_user = create_test_user(db_session, username="svc_user_2")

    # Add earning with negative amount raises ValueError
    with pytest.raises(ValueError):
        service.add_earning("dummy_id", amount=-10.0)

    with pytest.raises(ValueError):
        service.add_earning("dummy_id", amount=0.0)

    # Request payout with <= 0 raises ValueError
    with pytest.raises(ValueError):
        service.request_payout(creator, PayoutRequest(amount=0.0))

    # Request payout with insufficient funds raises ValueError
    with pytest.raises(ValueError, match="Insufficient Funds"):
        service.request_payout(creator, PayoutRequest(amount=100.0))

    # Get non-existent wallet / transaction / payout raises LookupError
    with pytest.raises(LookupError):
        service.get_wallet_by_id("non-existent", creator)

    with pytest.raises(LookupError):
        service.get_transaction_by_id("non-existent", creator)

    with pytest.raises(LookupError):
        service.get_payout_by_id("non-existent", creator)

    # Get wallet of other user raises PermissionError
    wallet = service.get_or_create_wallet(creator)
    with pytest.raises(PermissionError):
        service.get_wallet_by_id(wallet.id, other_user)


def test_payout_subcent_rejection(client: TestClient, db_session: Session):
    """Sub-cent amounts (e.g. 0.001) that round to 0.00 are rejected."""
    creator = create_test_user(db_session, username="subcent_user")
    headers = auth_headers(creator.id)

    resp = client.post("/api/v1/wallet/payout", json={"amount": 0.001}, headers=headers)
    assert resp.status_code in (400, 422)

    resp2 = client.post("/api/v1/wallet/payout", json={"amount": 0.004}, headers=headers)
    assert resp2.status_code in (400, 422)


def test_singular_alias_endpoints(client: TestClient, db_session: Session):
    """Singular path aliases /payout/{id} and /transaction/{id} work identically to plural."""
    creator = create_test_user(db_session, username="alias_routes_user")
    headers = auth_headers(creator.id)

    client.get("/api/v1/wallet", headers=headers)
    wallet = db_session.query(Wallet).filter(Wallet.user_id == creator.id).one()
    db_session.add(
        WalletTransaction(wallet_id=wallet.id, type=WalletTransactionType.CREATOR_EARNING, amount=500.0)
    )
    db_session.commit()

    resp_po = client.post("/api/v1/wallet/payout", json={"amount": 100.0}, headers=headers)
    assert resp_po.status_code == 201
    payout_id = resp_po.json()["id"]

    # Singular /payout/{id}
    resp_single_po = client.get(f"/api/v1/wallet/payout/{payout_id}", headers=headers)
    assert resp_single_po.status_code == 200
    assert resp_single_po.json()["id"] == payout_id

    # Find the debit transaction
    tx = db_session.query(WalletTransaction).filter(WalletTransaction.reference_id == payout_id).first()
    assert tx is not None

    # Singular /transaction/{id}
    resp_single_tx = client.get(f"/api/v1/wallet/transaction/{tx.id}", headers=headers)
    assert resp_single_tx.status_code == 200
    assert resp_single_tx.json()["id"] == tx.id


def test_wallet_not_found_endpoints(client: TestClient, db_session: Session):
    """Requesting non-existent resources returns HTTP 404."""
    creator = create_test_user(db_session, username="not_found_user")
    headers = auth_headers(creator.id)

    assert client.get("/api/v1/wallet/non-existent-id", headers=headers).status_code == 404
    assert client.get("/api/v1/wallet/payouts/non-existent-id", headers=headers).status_code == 404
    assert client.get("/api/v1/wallet/transactions/non-existent-id", headers=headers).status_code == 404


def test_model_properties_with_unbooked_and_booked_payouts(db_session: Session):
    """Verify in-memory model calculations for balance, available_balance, and pending_payout_balance."""
    creator = create_test_user(db_session, username="model_prop_user")
    wallet = Wallet(user_id=creator.id)
    db_session.add(wallet)
    db_session.commit()
    db_session.refresh(wallet)

    assert wallet.balance == 0.0
    assert wallet.available_balance == 0.0
    assert wallet.pending_payout_balance == 0.0

    # Add 1000 earning
    t1 = WalletTransaction(wallet_id=wallet.id, type=WalletTransactionType.CREATOR_EARNING, amount=1000.0)
    db_session.add(t1)
    db_session.commit()
    db_session.refresh(wallet)

    assert wallet.balance == 1000.0
    assert wallet.available_balance == 1000.0

    # Add unbooked pending payout of 300
    p1 = Payout(wallet_id=wallet.id, user_id=creator.id, amount=300.0, status=PayoutStatus.PENDING, payout_method={})
    db_session.add(p1)
    db_session.commit()
    db_session.refresh(wallet)

    # balance is still 1000, available_balance drops to 700, pending is 300
    assert wallet.balance == 1000.0
    assert wallet.available_balance == 700.0
    assert wallet.pending_payout_balance == 300.0

    # Book payout to ledger
    t2 = WalletTransaction(wallet_id=wallet.id, type=WalletTransactionType.PAYOUT, amount=-300.0, reference_id=p1.id)
    db_session.add(t2)
    db_session.commit()
    db_session.refresh(wallet)

    # Now both balance and available_balance are 700, pending is still 300
    assert wallet.balance == 700.0
    assert wallet.available_balance == 700.0
    assert wallet.pending_payout_balance == 300.0


def test_payout_boolean_rejection(client: TestClient, db_session: Session):
    """Boolean amount values (e.g. True/False) in payout requests are rejected."""
    creator = create_test_user(db_session, username="bool_amount_user")
    headers = auth_headers(creator.id)

    resp_true = client.post("/api/v1/wallet/payout", json={"amount": True}, headers=headers)
    assert resp_true.status_code in (400, 422)

    resp_false = client.post("/api/v1/wallet/payout", json={"amount": False}, headers=headers)
    assert resp_false.status_code in (400, 422)


def test_repository_zero_amount_transaction_rejection(db_session: Session):
    """Immutable ledger rejects adding zero or sub-cent zero-rounding transactions."""
    creator = create_test_user(db_session, username="zero_tx_user")
    repo = WalletRepository(db_session)
    wallet = repo.get_or_create_wallet(creator.id)

    with pytest.raises(ValueError, match="Transaction amount cannot be zero."):
        repo.add_transaction(wallet.id, WalletTransactionType.CREATOR_EARNING, amount=0.0)

    with pytest.raises(ValueError, match="Transaction amount cannot be zero."):
        repo.add_transaction(wallet.id, WalletTransactionType.CREATOR_EARNING, amount=0.001)


def test_singular_transaction_listing_alias(client: TestClient, db_session: Session):
    """Singular /transaction route alias returns list of transactions matching /transactions."""
    creator = create_test_user(db_session, username="single_tx_alias_user")
    headers = auth_headers(creator.id)

    client.get("/api/v1/wallet", headers=headers)
    wallet = db_session.query(Wallet).filter(Wallet.user_id == creator.id).one()
    db_session.add(
        WalletTransaction(
            wallet_id=wallet.id,
            type=WalletTransactionType.CREATOR_EARNING,
            amount=250.0,
            description="Test Tx",
        )
    )
    db_session.commit()

    resp_plural = client.get("/api/v1/wallet/transactions", headers=headers)
    resp_singular = client.get("/api/v1/wallet/transaction", headers=headers)

    assert resp_plural.status_code == 200
    assert resp_singular.status_code == 200
    assert resp_plural.json() == resp_singular.json()


def test_repository_pagination_bounds_safety(db_session: Session):
    """Repository gracefully clamps negative skip and invalid limit values."""
    creator = create_test_user(db_session, username="bounds_test_user")
    repo = WalletRepository(db_session)
    wallet = repo.get_or_create_wallet(creator.id)

    # Safe pagination even with negative offset or out-of-range limit
    txns = repo.get_transactions(wallet.id, skip=-10, limit=-5)
    assert isinstance(txns, list)

    payouts = repo.get_payouts_by_user(creator.id, skip=-1, limit=500)
    assert isinstance(payouts, list)


def test_payout_listing_trailing_slash_alias(client: TestClient, db_session: Session):
    """GET /api/v1/wallet/payout/ with trailing slash returns list of payouts matching /payouts."""
    creator = create_test_user(db_session, username="payout_slash_user")
    headers = auth_headers(creator.id)

    client.get("/api/v1/wallet", headers=headers)
    wallet = db_session.query(Wallet).filter(Wallet.user_id == creator.id).one()
    db_session.add(
        WalletTransaction(wallet_id=wallet.id, type=WalletTransactionType.CREATOR_EARNING, amount=1000.0)
    )
    db_session.commit()

    # Create payout
    resp_create = client.post("/api/v1/wallet/payout", json={"amount": 200.0}, headers=headers)
    assert resp_create.status_code == 201

    resp_plural = client.get("/api/v1/wallet/payouts", headers=headers)
    resp_slash = client.get("/api/v1/wallet/payout/", headers=headers)

    assert resp_plural.status_code == 200
    assert resp_slash.status_code == 200
    assert resp_slash.json() == resp_plural.json()
    assert len(resp_slash.json()) == 1


def test_wallet_me_endpoint_alias(client: TestClient, db_session: Session):
    """GET /api/v1/wallet/me and /api/v1/wallet/me/ correctly return current creator wallet."""
    creator = create_test_user(db_session, username="wallet_me_user")
    headers = auth_headers(creator.id)

    resp_root = client.get("/api/v1/wallet", headers=headers)
    resp_me = client.get("/api/v1/wallet/me", headers=headers)
    resp_me_slash = client.get("/api/v1/wallet/me/", headers=headers)

    assert resp_root.status_code == 200
    assert resp_me.status_code == 200
    assert resp_me_slash.status_code == 200
    assert resp_me.json()["id"] == resp_root.json()["id"]
    assert resp_me_slash.json()["id"] == resp_root.json()["id"]


def test_list_payouts_status_alias(client: TestClient, db_session: Session):
    """Filter payouts using payout_status query parameter alias."""
    creator = create_test_user(db_session, username="payout_alias_user")
    headers = auth_headers(creator.id)

    client.get("/api/v1/wallet", headers=headers)
    wallet = db_session.query(Wallet).filter(Wallet.user_id == creator.id).one()
    db_session.add(
        WalletTransaction(wallet_id=wallet.id, type=WalletTransactionType.CREATOR_EARNING, amount=500.0)
    )
    db_session.commit()

    client.post("/api/v1/wallet/payout", json={"amount": 100.0}, headers=headers)

    resp_filter_status = client.get("/api/v1/wallet/payouts?status=PENDING", headers=headers)
    resp_filter_alias = client.get("/api/v1/wallet/payouts?payout_status=PENDING", headers=headers)

    assert resp_filter_status.status_code == 200
    assert resp_filter_alias.status_code == 200
    assert resp_filter_alias.json() == resp_filter_status.json()


def test_wallet_service_update_payout_status_lifecycle(db_session: Session):
    """WalletService.update_payout_status supports full lifecycle and auto-refunds on REJECTED."""
    creator = create_test_user(db_session, username="svc_lifecycle_user")
    service = WalletService(db_session)
    wallet_resp = service.get_or_create_wallet(creator)

    # Fund wallet with 1000
    service.add_earning(wallet_resp.id, amount=1000.0)
    assert service.wallet_repo.get_available_balance(wallet_resp.id) == 1000.0

    # Request payout 300
    payout = service.request_payout(creator, PayoutRequest(amount=300.0))
    assert payout.status == PayoutStatus.PENDING
    assert service.wallet_repo.get_available_balance(wallet_resp.id) == 700.0
    assert service.wallet_repo.get_pending_payout_balance(wallet_resp.id) == 300.0

    # Transition to PROCESSING
    updated_proc = service.update_payout_status(payout.id, PayoutStatus.PROCESSING)
    assert updated_proc.status == PayoutStatus.PROCESSING
    assert service.wallet_repo.get_available_balance(wallet_resp.id) == 700.0

    # Transition to REJECTED -> automatically credits back 300 via ADJUSTMENT transaction
    updated_rej = service.update_payout_status(payout.id, PayoutStatus.REJECTED, reason="Invalid IFSC")
    assert updated_rej.status == PayoutStatus.REJECTED
    assert service.wallet_repo.get_available_balance(wallet_resp.id) == 1000.0
    assert service.wallet_repo.get_pending_payout_balance(wallet_resp.id) == 0.0

    # Check that the ADJUSTMENT transaction was added to the immutable ledger
    adj_tx = (
        db_session.query(WalletTransaction)
        .filter(
            WalletTransaction.wallet_id == wallet_resp.id,
            WalletTransaction.type == WalletTransactionType.ADJUSTMENT,
            WalletTransaction.reference_id == payout.id,
        )
        .first()
    )
    assert adj_tx is not None
    assert adj_tx.amount == 300.0


def test_wallet_service_update_payout_terminal_state_rejection(db_session: Session):
    """Updating a payout that is already COMPLETED or REJECTED raises ValueError."""
    creator = create_test_user(db_session, username="svc_terminal_user")
    service = WalletService(db_session)
    wallet_resp = service.get_or_create_wallet(creator)

    service.add_earning(wallet_resp.id, amount=500.0)
    payout = service.request_payout(creator, PayoutRequest(amount=200.0))

    # Complete it
    service.update_payout_status(payout.id, PayoutStatus.COMPLETED)

    # Attempt to change completed payout raises ValueError
    with pytest.raises(ValueError, match="terminal state"):
        service.update_payout_status(payout.id, PayoutStatus.REJECTED)

    # Attempt to update non-existent payout raises LookupError
    with pytest.raises(LookupError):
        service.update_payout_status("non-existent-id", PayoutStatus.COMPLETED)




