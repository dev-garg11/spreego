from datetime import datetime, timezone
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.config.database import Base
from src.config.security import create_access_token
from src.models.commerce import (
    Order,
    OrderItem,
    OrderStatus,
    Product,
    ProductType,
)
from src.models.profile import Profile
from src.models.user import User


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
    phone = phone_number or f"+9198{uid[:6]}"
    mail = email or f"user_{uid}@spreego.com"
    handle = username or f"user_{uid}"

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
        full_name=f"User {handle}",
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
# 1. Database & Metadata Verification
# ============================================================================

def test_commerce_models_registered_in_base_metadata():
    """Verify products, orders, and order_items tables are in Base metadata."""
    assert "products" in Base.metadata.tables
    assert "orders" in Base.metadata.tables
    assert "order_items" in Base.metadata.tables

    prod_table = Base.metadata.tables["products"]
    assert "id" in prod_table.columns
    assert "creator_id" in prod_table.columns
    assert "type" in prod_table.columns
    assert "title" in prod_table.columns
    assert "description" in prod_table.columns
    assert "price" in prod_table.columns
    assert "currency" in prod_table.columns
    assert "images" in prod_table.columns
    assert "inventory" in prod_table.columns
    assert "is_active" in prod_table.columns
    assert "created_at" in prod_table.columns
    assert "updated_at" in prod_table.columns

    order_table = Base.metadata.tables["orders"]
    assert "id" in order_table.columns
    assert "buyer_id" in order_table.columns
    assert "seller_id" in order_table.columns
    assert "total_amount" in order_table.columns
    assert "status" in order_table.columns
    assert "shipping_address" in order_table.columns
    assert "created_at" in order_table.columns
    assert "updated_at" in order_table.columns

    item_table = Base.metadata.tables["order_items"]
    assert "id" in item_table.columns
    assert "order_id" in item_table.columns
    assert "product_id" in item_table.columns
    assert "quantity" in item_table.columns
    assert "unit_price" in item_table.columns
    assert "subtotal" in item_table.columns


def test_commerce_direct_model_instantiation(db_session: Session):
    """Direct model instantiation and relationship checks in database."""
    creator = create_test_user(db_session, username="direct_creator")
    buyer = create_test_user(db_session, username="direct_buyer")

    prod = Product(
        creator_id=creator.id,
        type=ProductType.PHYSICAL,
        title="Direct T-Shirt",
        price=499.0,
        inventory=10,
    )
    db_session.add(prod)
    db_session.commit()
    db_session.refresh(prod)

    assert prod.id is not None
    assert prod.currency == "INR"
    assert prod.is_active is True
    assert prod.is_in_stock is True
    assert prod.creator.id == creator.id

    order = Order(
        buyer_id=buyer.id,
        seller_id=creator.id,
        total_amount=998.0,
        status=OrderStatus.CREATED,
        shipping_address={"city": "Bengaluru", "pincode": "560001"},
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)

    item = OrderItem(
        order_id=order.id,
        product_id=prod.id,
        quantity=2,
        unit_price=499.0,
        subtotal=998.0,
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(order)

    assert len(order.items) == 1
    assert order.items[0].product.title == "Direct T-Shirt"
    assert order.buyer.id == buyer.id
    assert order.seller.id == creator.id


# ============================================================================
# 2. Product CRUD & Ownership Security
# ============================================================================

def test_create_product_authenticated(client: TestClient, db_session: Session):
    """Authenticated creator lists a new product with creator_id from JWT."""
    creator = create_test_user(db_session, username="prod_creator_1")
    headers = auth_headers(creator.id)

    payload = {
        "type": "PHYSICAL",
        "title": "SPREEGO Cap",
        "description": "Official cotton cap",
        "price": 299.0,
        "currency": "INR",
        "images": ["https://spreego.com/cap.png"],
        "inventory": 25,
        "is_active": True,
    }
    resp = client.post("/api/v1/products", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] is not None
    assert data["creator_id"] == creator.id
    assert data["title"] == "SPREEGO Cap"
    assert data["price"] == 299.0
    assert data["inventory"] == 25
    assert data["is_active"] is True
    assert data["images"] == ["https://spreego.com/cap.png"]


def test_create_product_unauthenticated_returns_401(client: TestClient):
    """Unauthenticated product creation returns HTTP 401."""
    resp = client.post("/api/v1/products", json={"title": "Unauthorized Item", "price": 100})
    assert resp.status_code == 401


def test_create_product_validation_errors(client: TestClient, db_session: Session):
    """Product creation with invalid data returns HTTP 422."""
    creator = create_test_user(db_session, username="val_creator")
    headers = auth_headers(creator.id)

    # Empty title
    resp = client.post("/api/v1/products", json={"title": "   ", "price": 50}, headers=headers)
    assert resp.status_code == 422

    # Negative price
    resp = client.post("/api/v1/products", json={"title": "Item", "price": -10}, headers=headers)
    assert resp.status_code == 422

    # Negative inventory
    resp = client.post("/api/v1/products", json={"title": "Item", "price": 10, "inventory": -5}, headers=headers)
    assert resp.status_code == 422


def test_get_product_public_lookup(client: TestClient, db_session: Session):
    """Public product details lookup returns 200 without auth."""
    creator = create_test_user(db_session, username="pub_lookup_creator")
    prod = Product(
        creator_id=creator.id,
        type=ProductType.DIGITAL,
        title="E-Book Guide",
        price=199.0,
        inventory=0,
    )
    db_session.add(prod)
    db_session.commit()

    resp = client.get(f"/api/v1/products/{prod.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == prod.id
    assert data["title"] == "E-Book Guide"
    assert data["type"] == "DIGITAL"
    assert data["price"] == 199.0


def test_get_nonexistent_product_returns_404(client: TestClient):
    """Lookup of non-existent product returns HTTP 404."""
    resp = client.get("/api/v1/products/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_list_products_filtering_and_pagination(client: TestClient, db_session: Session):
    """List products with filters (creator_id, type, is_active) and pagination."""
    creator1 = create_test_user(db_session, username="filter_c1")
    creator2 = create_test_user(db_session, username="filter_c2")

    # Seed products
    p1 = Product(creator_id=creator1.id, type=ProductType.PHYSICAL, title="C1 Physical", price=100, is_active=True)
    p2 = Product(creator_id=creator1.id, type=ProductType.DIGITAL, title="C1 Digital", price=50, is_active=False)
    p3 = Product(creator_id=creator2.id, type=ProductType.SERVICE, title="C2 Service", price=500, is_active=True)
    db_session.add_all([p1, p2, p3])
    db_session.commit()

    # Filter by creator_id
    resp = client.get(f"/api/v1/products?creator_id={creator1.id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 2
    assert all(p["creator_id"] == creator1.id for p in resp.json())

    # Filter by type
    resp = client.get(f"/api/v1/products?type=DIGITAL")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["title"] == "C1 Digital"

    # Filter by is_active
    resp = client.get(f"/api/v1/products?is_active=false")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["is_active"] is False

    resp = client.get(f"/api/v1/products?is_active=true")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    # Pagination: limit
    resp = client.get(f"/api/v1/products?limit=1")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_patch_product_ownership_security(client: TestClient, db_session: Session):
    """Owner can update product; non-owner is rejected with HTTP 403."""
    owner = create_test_user(db_session, username="patch_owner")
    attacker = create_test_user(db_session, username="patch_attacker")

    prod = Product(creator_id=owner.id, type=ProductType.PHYSICAL, title="Initial Shirt", price=200, inventory=5)
    db_session.add(prod)
    db_session.commit()

    # Non-owner attempt -> 403
    resp_attacker = client.patch(
        f"/api/v1/products/{prod.id}",
        json={"title": "Hacked Shirt", "price": 1},
        headers=auth_headers(attacker.id),
    )
    assert resp_attacker.status_code == 403

    # Owner update -> 200
    resp_owner = client.patch(
        f"/api/v1/products/{prod.id}",
        json={"title": "Updated Shirt", "price": 250.0, "inventory": 12},
        headers=auth_headers(owner.id),
    )
    assert resp_owner.status_code == 200
    data = resp_owner.json()
    assert data["title"] == "Updated Shirt"
    assert data["price"] == 250.0
    assert data["inventory"] == 12


def test_patch_product_tamper_protected_fields_ignored(client: TestClient, db_session: Session):
    """Attempting to tamper with protected fields (id, creator_id) in PATCH is safely ignored."""
    owner = create_test_user(db_session, username="tamper_prod_owner")
    attacker = create_test_user(db_session, username="tamper_prod_attacker")

    prod = Product(creator_id=owner.id, type=ProductType.PHYSICAL, title="Original Product", price=100)
    db_session.add(prod)
    db_session.commit()

    resp = client.patch(
        f"/api/v1/products/{prod.id}",
        json={
            "title": "Renamed Product",
            "creator_id": attacker.id,
            "id": "fake-uuid-attack",
        },
        headers=auth_headers(owner.id),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == prod.id
    assert data["creator_id"] == owner.id
    assert data["title"] == "Renamed Product"


def test_delete_product_ownership_security(client: TestClient, db_session: Session):
    """Owner can delete product; non-owner is rejected with HTTP 403."""
    owner = create_test_user(db_session, username="del_owner")
    attacker = create_test_user(db_session, username="del_attacker")

    prod = Product(creator_id=owner.id, type=ProductType.PHYSICAL, title="To Delete", price=50)
    db_session.add(prod)
    db_session.commit()

    # Attacker tries to delete -> 403
    resp_attacker = client.delete(f"/api/v1/products/{prod.id}", headers=auth_headers(attacker.id))
    assert resp_attacker.status_code == 403

    # Owner deletes -> 200
    resp_owner = client.delete(f"/api/v1/products/{prod.id}", headers=auth_headers(owner.id))
    assert resp_owner.status_code == 200

    # Ensure deleted
    resp_check = client.get(f"/api/v1/products/{prod.id}")
    assert resp_check.status_code == 404


# ============================================================================
# 3. Order Creation & Pricing Security (Server-Derived Calculations)
# ============================================================================

def test_order_creation_server_derived_pricing(client: TestClient, db_session: Session):
    """Server calculates total_amount and subtotal from database prices; client tampering ignored."""
    seller = create_test_user(db_session, username="store_seller_1")
    buyer = create_test_user(db_session, username="store_buyer_1")

    p1 = Product(creator_id=seller.id, type=ProductType.PHYSICAL, title="Hoodie", price=1200.0, inventory=10)
    p2 = Product(creator_id=seller.id, type=ProductType.PHYSICAL, title="Mug", price=300.0, inventory=20)
    db_session.add_all([p1, p2])
    db_session.commit()

    # Client attempts price tampering by passing unit_price: 1.0 and total_amount: 5.0
    payload = {
        "items": [
            {"product_id": p1.id, "quantity": 2, "unit_price": 1.0, "subtotal": 2.0},
            {"product_id": p2.id, "quantity": 1, "unit_price": 1.0, "subtotal": 1.0},
        ],
        "total_amount": 3.0,
        "shipping_address": {"street": "123 MG Road", "city": "Bengaluru"},
    }

    resp = client.post("/api/v1/orders", json=payload, headers=auth_headers(buyer.id))
    assert resp.status_code == 201
    order_data = resp.json()

    # Server price: (1200 * 2) + (300 * 1) = 2700.0
    assert order_data["total_amount"] == 2700.0
    assert order_data["total_amount"] != 3.0
    assert order_data["buyer_id"] == buyer.id
    assert order_data["seller_id"] == seller.id
    assert order_data["status"] == "CREATED"

    items = order_data["items"]
    assert len(items) == 2
    item1 = next(it for it in items if it["product_id"] == p1.id)
    assert item1["unit_price"] == 1200.0
    assert item1["subtotal"] == 2400.0

    item2 = next(it for it in items if it["product_id"] == p2.id)
    assert item2["unit_price"] == 300.0
    assert item2["subtotal"] == 300.0


def test_order_creation_unit_price_frozen_at_purchase(client: TestClient, db_session: Session):
    """Subsequent product price edits do not alter historical order item unit prices."""
    seller = create_test_user(db_session, username="price_change_seller")
    buyer = create_test_user(db_session, username="price_change_buyer")

    prod = Product(creator_id=seller.id, type=ProductType.PHYSICAL, title="Widget", price=100.0, inventory=10)
    db_session.add(prod)
    db_session.commit()

    # Place order at price 100.0
    resp_order = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": prod.id, "quantity": 1}]},
        headers=auth_headers(buyer.id),
    )
    assert resp_order.status_code == 201
    order_id = resp_order.json()["id"]

    # Seller updates product price to 500.0
    prod.price = 500.0
    db_session.commit()

    # Existing order item remains frozen at 100.0
    resp_get = client.get(f"/api/v1/orders/{order_id}", headers=auth_headers(buyer.id))
    assert resp_get.status_code == 200
    assert resp_get.json()["total_amount"] == 100.0
    assert resp_get.json()["items"][0]["unit_price"] == 100.0


def test_order_creation_mixed_sellers_rejected(client: TestClient, db_session: Session):
    """Placing an order with products from multiple distinct sellers returns HTTP 400."""
    seller1 = create_test_user(db_session, username="multi_seller_1")
    seller2 = create_test_user(db_session, username="multi_seller_2")
    buyer = create_test_user(db_session, username="multi_buyer")

    p1 = Product(creator_id=seller1.id, type=ProductType.PHYSICAL, title="P1", price=50, inventory=10)
    p2 = Product(creator_id=seller2.id, type=ProductType.PHYSICAL, title="P2", price=75, inventory=10)
    db_session.add_all([p1, p2])
    db_session.commit()

    resp = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": p1.id, "quantity": 1}, {"product_id": p2.id, "quantity": 1}]},
        headers=auth_headers(buyer.id),
    )
    assert resp.status_code == 400
    assert "same seller" in resp.json()["detail"].lower()


def test_order_creation_inactive_product_rejected(client: TestClient, db_session: Session):
    """Ordering an inactive product returns HTTP 400."""
    seller = create_test_user(db_session, username="inactive_prod_seller")
    buyer = create_test_user(db_session, username="inactive_prod_buyer")

    prod = Product(creator_id=seller.id, type=ProductType.PHYSICAL, title="Deactivated", price=100, inventory=10, is_active=False)
    db_session.add(prod)
    db_session.commit()

    resp = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": prod.id, "quantity": 1}]},
        headers=auth_headers(buyer.id),
    )
    assert resp.status_code == 400


# ============================================================================
# 4. Inventory Management (Decrement, Out-of-Stock, and Restoration)
# ============================================================================

def test_order_out_of_stock_rejected_with_400(client: TestClient, db_session: Session):
    """Order fails with HTTP 400 if quantity exceeds available stock."""
    seller = create_test_user(db_session, username="stock_seller")
    buyer = create_test_user(db_session, username="stock_buyer")

    prod = Product(creator_id=seller.id, type=ProductType.PHYSICAL, title="Limited Edition Watch", price=5000.0, inventory=2)
    db_session.add(prod)
    db_session.commit()

    # Request 3 items when only 2 available
    resp = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": prod.id, "quantity": 3}]},
        headers=auth_headers(buyer.id),
    )
    assert resp.status_code == 400
    assert "insufficient" in resp.json()["detail"].lower()

    # Inventory remains untouched
    db_session.refresh(prod)
    assert prod.inventory == 2


def test_inventory_decrement_and_restoration_on_cancellation(client: TestClient, db_session: Session):
    """Inventory decrements upon purchase and restores upon order cancellation."""
    seller = create_test_user(db_session, username="inv_seller")
    buyer = create_test_user(db_session, username="inv_buyer")

    prod = Product(creator_id=seller.id, type=ProductType.PHYSICAL, title="Sneakers", price=2500.0, inventory=5)
    db_session.add(prod)
    db_session.commit()

    # 1. Place order for 3 items
    resp_order = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": prod.id, "quantity": 3}]},
        headers=auth_headers(buyer.id),
    )
    assert resp_order.status_code == 201
    order_id = resp_order.json()["id"]

    # Verify inventory was decremented to 2
    db_session.refresh(prod)
    assert prod.inventory == 2

    # 2. Cancel order
    resp_cancel = client.post(f"/api/v1/orders/{order_id}/cancel", headers=auth_headers(buyer.id))
    assert resp_cancel.status_code == 200
    assert resp_cancel.json()["status"] == "CANCELLED"

    # Verify inventory restored back to 5
    db_session.refresh(prod)
    assert prod.inventory == 5


def test_cannot_cancel_already_cancelled_order(client: TestClient, db_session: Session):
    """Attempting to cancel an already cancelled order returns HTTP 400."""
    seller = create_test_user(db_session, username="double_cancel_seller")
    buyer = create_test_user(db_session, username="double_cancel_buyer")

    prod = Product(creator_id=seller.id, type=ProductType.PHYSICAL, title="Stickers", price=50.0, inventory=10)
    db_session.add(prod)
    db_session.commit()

    resp_order = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": prod.id, "quantity": 1}]},
        headers=auth_headers(buyer.id),
    )
    order_id = resp_order.json()["id"]

    # First cancel succeeds
    client.post(f"/api/v1/orders/{order_id}/cancel", headers=auth_headers(buyer.id))

    # Second cancel fails with 400
    resp_second = client.post(f"/api/v1/orders/{order_id}/cancel", headers=auth_headers(buyer.id))
    assert resp_second.status_code == 400
    assert "already cancelled" in resp_second.json()["detail"].lower()


def test_cannot_cancel_shipped_or_delivered_order(client: TestClient, db_session: Session):
    """Attempting to cancel an order after shipping returns HTTP 400."""
    seller = create_test_user(db_session, username="shipped_seller")
    buyer = create_test_user(db_session, username="shipped_buyer")

    prod = Product(creator_id=seller.id, type=ProductType.PHYSICAL, title="Books", price=400.0, inventory=10)
    db_session.add(prod)
    db_session.commit()

    resp_order = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": prod.id, "quantity": 1}]},
        headers=auth_headers(buyer.id),
    )
    order_id = resp_order.json()["id"]

    # Seller updates status to SHIPPED
    resp_ship = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "SHIPPED"},
        headers=auth_headers(seller.id),
    )
    assert resp_ship.status_code == 200
    assert resp_ship.json()["status"] == "SHIPPED"

    # Buyer attempts to cancel -> 400
    resp_cancel = client.post(f"/api/v1/orders/{order_id}/cancel", headers=auth_headers(buyer.id))
    assert resp_cancel.status_code == 400
    assert "shipped or delivered" in resp_cancel.json()["detail"].lower()


# ============================================================================
# 5. Buyer/Seller Order Visibility Isolation
# ============================================================================

def test_order_visibility_isolation(client: TestClient, db_session: Session):
    """Buyer and seller can view order details; third-party user gets HTTP 403."""
    seller = create_test_user(db_session, username="vis_seller")
    buyer = create_test_user(db_session, username="vis_buyer")
    intruder = create_test_user(db_session, username="vis_intruder")

    prod = Product(creator_id=seller.id, type=ProductType.DIGITAL, title="Artwork", price=800.0, inventory=0)
    db_session.add(prod)
    db_session.commit()

    resp_order = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": prod.id, "quantity": 1}]},
        headers=auth_headers(buyer.id),
    )
    order_id = resp_order.json()["id"]

    # Buyer lookup -> 200
    resp_buyer = client.get(f"/api/v1/orders/{order_id}", headers=auth_headers(buyer.id))
    assert resp_buyer.status_code == 200

    # Seller lookup -> 200
    resp_seller = client.get(f"/api/v1/orders/{order_id}", headers=auth_headers(seller.id))
    assert resp_seller.status_code == 200

    # Intruder lookup -> 403 Forbidden
    resp_intruder = client.get(f"/api/v1/orders/{order_id}", headers=auth_headers(intruder.id))
    assert resp_intruder.status_code == 403

    # Intruder cancel -> 403 Forbidden
    resp_intruder_cancel = client.post(f"/api/v1/orders/{order_id}/cancel", headers=auth_headers(intruder.id))
    assert resp_intruder_cancel.status_code == 403


def test_get_my_orders_returns_only_current_users_orders(client: TestClient, db_session: Session):
    """GET /api/v1/orders/my returns only orders placed by the current user."""
    seller = create_test_user(db_session, username="my_seller")
    buyer1 = create_test_user(db_session, username="my_buyer1")
    buyer2 = create_test_user(db_session, username="my_buyer2")

    p = Product(creator_id=seller.id, type=ProductType.DIGITAL, title="Poster", price=150.0)
    db_session.add(p)
    db_session.commit()

    # Buyer 1 places 2 orders
    client.post("/api/v1/orders", json={"items": [{"product_id": p.id, "quantity": 1}]}, headers=auth_headers(buyer1.id))
    client.post("/api/v1/orders", json={"items": [{"product_id": p.id, "quantity": 2}]}, headers=auth_headers(buyer1.id))

    # Buyer 2 places 1 order
    client.post("/api/v1/orders", json={"items": [{"product_id": p.id, "quantity": 1}]}, headers=auth_headers(buyer2.id))

    # Buyer 1 gets their orders
    resp1 = client.get("/api/v1/orders/my", headers=auth_headers(buyer1.id))
    assert resp1.status_code == 200
    assert len(resp1.json()) == 2
    assert all(o["buyer_id"] == buyer1.id for o in resp1.json())

    # Buyer 2 gets their orders
    resp2 = client.get("/api/v1/orders/my", headers=auth_headers(buyer2.id))
    assert resp2.status_code == 200
    assert len(resp2.json()) == 1
    assert resp2.json()[0]["buyer_id"] == buyer2.id


# ============================================================================
# 6. Additional Edge Cases & Security Checks
# ============================================================================

def test_order_invalid_inputs_return_422(client: TestClient, db_session: Session):
    """Orders with invalid payload (empty items, quantity < 1) return HTTP 422."""
    buyer = create_test_user(db_session, username="edge_buyer_422")
    headers = auth_headers(buyer.id)

    # Empty items list
    resp1 = client.post("/api/v1/orders", json={"items": []}, headers=headers)
    assert resp1.status_code == 422

    # Quantity 0
    resp2 = client.post("/api/v1/orders", json={"items": [{"product_id": "fake", "quantity": 0}]}, headers=headers)
    assert resp2.status_code == 422

    # Negative quantity
    resp3 = client.post("/api/v1/orders", json={"items": [{"product_id": "fake", "quantity": -3}]}, headers=headers)
    assert resp3.status_code == 422


def test_order_nonexistent_product_returns_404(client: TestClient, db_session: Session):
    """Ordering a non-existent product returns HTTP 404."""
    buyer = create_test_user(db_session, username="edge_buyer_404")
    headers = auth_headers(buyer.id)

    resp = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": "00000000-0000-0000-0000-000000000000", "quantity": 1}]},
        headers=headers,
    )
    assert resp.status_code == 404


def test_order_endpoints_unauthenticated_return_401(client: TestClient):
    """Unauthenticated access to order endpoints returns HTTP 401."""
    assert client.post("/api/v1/orders", json={"items": []}).status_code == 401
    assert client.get("/api/v1/orders/my").status_code == 401
    assert client.get("/api/v1/orders/fake-id").status_code == 401
    assert client.post("/api/v1/orders/fake-id/cancel").status_code == 401
    assert client.patch("/api/v1/orders/fake-id/status", json={"status": "SHIPPED"}).status_code == 401


def test_product_patch_and_delete_nonexistent_returns_404(client: TestClient, db_session: Session):
    """Patching or deleting non-existent product returns HTTP 404."""
    user = create_test_user(db_session, username="edge_prod_user")
    headers = auth_headers(user.id)
    fake_id = "00000000-0000-0000-0000-000000000000"

    resp_patch = client.patch(f"/api/v1/products/{fake_id}", json={"title": "New"}, headers=headers)
    assert resp_patch.status_code == 404

    resp_del = client.delete(f"/api/v1/products/{fake_id}", headers=headers)
    assert resp_del.status_code == 404


def test_order_status_update_permissions(client: TestClient, db_session: Session):
    """Only the seller can update order status; buyer and others get HTTP 403."""
    seller = create_test_user(db_session, username="status_seller")
    buyer = create_test_user(db_session, username="status_buyer")
    other = create_test_user(db_session, username="status_other")

    prod = Product(creator_id=seller.id, type=ProductType.DIGITAL, title="PDF Book", price=250.0)
    db_session.add(prod)
    db_session.commit()

    resp_order = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": prod.id, "quantity": 1}]},
        headers=auth_headers(buyer.id),
    )
    order_id = resp_order.json()["id"]

    # Buyer cannot update status -> 403
    resp_buyer = client.patch(f"/api/v1/orders/{order_id}/status", json={"status": "PROCESSING"}, headers=auth_headers(buyer.id))
    assert resp_buyer.status_code == 403

    # Other cannot update status -> 403
    resp_other = client.patch(f"/api/v1/orders/{order_id}/status", json={"status": "PROCESSING"}, headers=auth_headers(other.id))
    assert resp_other.status_code == 403

    # Seller can update status -> 200
    resp_seller = client.patch(f"/api/v1/orders/{order_id}/status", json={"status": "PROCESSING"}, headers=auth_headers(seller.id))
    assert resp_seller.status_code == 200
    assert resp_seller.json()["status"] == "PROCESSING"


def test_digital_and_service_products_order_without_inventory(client: TestClient, db_session: Session):
    """Digital and service products can be ordered with zero inventory without decrement."""
    seller = create_test_user(db_session, username="digital_seller")
    buyer = create_test_user(db_session, username="digital_buyer")

    prod_dig = Product(creator_id=seller.id, type=ProductType.DIGITAL, title="Software License", price=1999.0, inventory=0)
    prod_srv = Product(creator_id=seller.id, type=ProductType.SERVICE, title="1-on-1 Consultation", price=2999.0, inventory=0)
    db_session.add_all([prod_dig, prod_srv])
    db_session.commit()

    resp_dig = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": prod_dig.id, "quantity": 5}]},
        headers=auth_headers(buyer.id),
    )
    assert resp_dig.status_code == 201
    assert resp_dig.json()["total_amount"] == 1999.0 * 5

    # Inventory remains 0 and was not decremented to negative
    db_session.refresh(prod_dig)
    assert prod_dig.inventory == 0

    resp_srv = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": prod_srv.id, "quantity": 1}]},
        headers=auth_headers(buyer.id),
    )
    assert resp_srv.status_code == 201
    assert resp_srv.json()["total_amount"] == 2999.0


def test_order_cancellation_by_seller_restores_inventory(client: TestClient, db_session: Session):
    """Seller can cancel an order and it restores physical inventory."""
    seller = create_test_user(db_session, username="seller_cancels")
    buyer = create_test_user(db_session, username="buyer_cancelled")

    prod = Product(creator_id=seller.id, type=ProductType.PHYSICAL, title="Poster", price=200.0, inventory=10)
    db_session.add(prod)
    db_session.commit()

    resp_order = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": prod.id, "quantity": 4}]},
        headers=auth_headers(buyer.id),
    )
    order_id = resp_order.json()["id"]

    db_session.refresh(prod)
    assert prod.inventory == 6

    # Seller cancels
    resp_cancel = client.post(f"/api/v1/orders/{order_id}/cancel", headers=auth_headers(seller.id))
    assert resp_cancel.status_code == 200
    assert resp_cancel.json()["status"] == "CANCELLED"

    db_session.refresh(prod)
    assert prod.inventory == 10


def test_order_duplicate_items_aggregate_stock_check(client: TestClient, db_session: Session):
    """Multiple items in the same order referencing the same product must aggregate quantities against stock."""
    seller = create_test_user(db_session, username="dup_seller")
    buyer = create_test_user(db_session, username="dup_buyer")

    prod = Product(creator_id=seller.id, type=ProductType.PHYSICAL, title="Rare Coin", price=1000.0, inventory=3)
    db_session.add(prod)
    db_session.commit()

    # 1. Attacker sends 2 line items of qty 2 each (total 4), exceeding stock of 3
    resp_fail = client.post(
        "/api/v1/orders",
        json={
            "items": [
                {"product_id": prod.id, "quantity": 2},
                {"product_id": prod.id, "quantity": 2},
            ]
        },
        headers=auth_headers(buyer.id),
    )
    assert resp_fail.status_code == 400
    assert "insufficient" in resp_fail.json()["detail"].lower()

    # Stock must remain untouched
    db_session.refresh(prod)
    assert prod.inventory == 3

    # 2. Valid duplicate items that sum to <= stock (1 + 2 = 3)
    resp_ok = client.post(
        "/api/v1/orders",
        json={
            "items": [
                {"product_id": prod.id, "quantity": 1},
                {"product_id": prod.id, "quantity": 2},
            ]
        },
        headers=auth_headers(buyer.id),
    )
    assert resp_ok.status_code == 201
    db_session.refresh(prod)
    assert prod.inventory == 0


def test_multi_item_order_partial_stock_failure_rolls_back_cleanly(client: TestClient, db_session: Session):
    """Ordering multiple items where item 1 has stock but item 2 is out of stock must not leak item 1 stock."""
    seller = create_test_user(db_session, username="multi_rollback_seller")
    buyer = create_test_user(db_session, username="multi_rollback_buyer")

    p1 = Product(creator_id=seller.id, type=ProductType.PHYSICAL, title="Product In Stock", price=100.0, inventory=10)
    p2 = Product(creator_id=seller.id, type=ProductType.PHYSICAL, title="Product Out of Stock", price=200.0, inventory=0)
    db_session.add_all([p1, p2])
    db_session.commit()

    resp = client.post(
        "/api/v1/orders",
        json={
            "items": [
                {"product_id": p1.id, "quantity": 5},
                {"product_id": p2.id, "quantity": 1},
            ]
        },
        headers=auth_headers(buyer.id),
    )
    assert resp.status_code == 400
    assert "insufficient" in resp.json()["detail"].lower()

    # Verify p1 stock was NOT decremented
    db_session.refresh(p1)
    assert p1.inventory == 10


def test_delete_product_with_existing_orders_rejected(client: TestClient, db_session: Session):
    """Deleting a product that has existing orders is rejected with HTTP 400 to protect order history."""
    seller = create_test_user(db_session, username="del_guard_seller")
    buyer = create_test_user(db_session, username="del_guard_buyer")

    prod = Product(creator_id=seller.id, type=ProductType.PHYSICAL, title="Ordered Item", price=300.0, inventory=5)
    db_session.add(prod)
    db_session.commit()

    # Buyer places order
    resp_order = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": prod.id, "quantity": 1}]},
        headers=auth_headers(buyer.id),
    )
    assert resp_order.status_code == 201
    order_id = resp_order.json()["id"]

    # Seller attempts to delete product -> 400
    resp_del = client.delete(f"/api/v1/products/{prod.id}", headers=auth_headers(seller.id))
    assert resp_del.status_code == 400
    assert "existing orders" in resp_del.json()["detail"].lower()

    # Order and order items remain intact
    resp_get = client.get(f"/api/v1/orders/{order_id}", headers=auth_headers(buyer.id))
    assert resp_get.status_code == 200
    assert len(resp_get.json()["items"]) == 1


def test_update_order_status_state_transitions(client: TestClient, db_session: Session):
    """Validates state transitions and terminal states in update_order_status."""
    seller = create_test_user(db_session, username="state_seller")
    buyer = create_test_user(db_session, username="state_buyer")

    prod = Product(creator_id=seller.id, type=ProductType.PHYSICAL, title="Transition Item", price=500.0, inventory=10)
    db_session.add(prod)
    db_session.commit()

    resp_order = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": prod.id, "quantity": 2}]},
        headers=auth_headers(buyer.id),
    )
    order_id = resp_order.json()["id"]
    db_session.refresh(prod)
    assert prod.inventory == 8

    # 1. Update status to CANCELLED via status endpoint restores inventory
    resp_cancel_via_patch = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "CANCELLED"},
        headers=auth_headers(seller.id),
    )
    assert resp_cancel_via_patch.status_code == 200
    assert resp_cancel_via_patch.json()["status"] == "CANCELLED"
    db_session.refresh(prod)
    assert prod.inventory == 10

    # 2. Attempting to update status of already CANCELLED order returns 400
    resp_resurrect = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "PROCESSING"},
        headers=auth_headers(seller.id),
    )
    assert resp_resurrect.status_code == 400
    assert "cancelled" in resp_resurrect.json()["detail"].lower()

    # 3. Create another order and deliver it
    resp_order2 = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": prod.id, "quantity": 1}]},
        headers=auth_headers(buyer.id),
    )
    order_id2 = resp_order2.json()["id"]

    client.patch(f"/api/v1/orders/{order_id2}/status", json={"status": "SHIPPED"}, headers=auth_headers(seller.id))
    client.patch(f"/api/v1/orders/{order_id2}/status", json={"status": "DELIVERED"}, headers=auth_headers(seller.id))

    # Cannot transition delivered order
    resp_deliv = client.patch(
        f"/api/v1/orders/{order_id2}/status",
        json={"status": "PROCESSING"},
        headers=auth_headers(seller.id),
    )
    assert resp_deliv.status_code == 400
    assert "delivered" in resp_deliv.json()["detail"].lower()


def test_get_store_orders_returns_orders_for_seller(client: TestClient, db_session: Session):
    """GET /api/v1/orders/store returns orders placed for current seller's store."""
    seller1 = create_test_user(db_session, username="store_s1")
    seller2 = create_test_user(db_session, username="store_s2")
    buyer = create_test_user(db_session, username="store_b1")

    p1 = Product(creator_id=seller1.id, type=ProductType.DIGITAL, title="Store 1 Product", price=100.0)
    p2 = Product(creator_id=seller2.id, type=ProductType.DIGITAL, title="Store 2 Product", price=200.0)
    db_session.add_all([p1, p2])
    db_session.commit()

    # Buyer orders from both sellers
    client.post("/api/v1/orders", json={"items": [{"product_id": p1.id, "quantity": 1}]}, headers=auth_headers(buyer.id))
    client.post("/api/v1/orders", json={"items": [{"product_id": p2.id, "quantity": 1}]}, headers=auth_headers(buyer.id))

    # Seller 1 views store orders
    resp_s1 = client.get("/api/v1/orders/store", headers=auth_headers(seller1.id))
    assert resp_s1.status_code == 200
    assert len(resp_s1.json()) == 1
    assert resp_s1.json()[0]["seller_id"] == seller1.id

    # Seller 2 views store orders
    resp_s2 = client.get("/api/v1/orders/store", headers=auth_headers(seller2.id))
    assert resp_s2.status_code == 200
    assert len(resp_s2.json()) == 1
    assert resp_s2.json()[0]["seller_id"] == seller2.id


def test_self_purchase_rejected(client: TestClient, db_session: Session):
    """Creators cannot purchase their own products."""
    creator = create_test_user(db_session, username="self_buyer_creator")
    prod = Product(creator_id=creator.id, type=ProductType.PHYSICAL, title="Self Item", price=100.0, inventory=5)
    db_session.add(prod)
    db_session.commit()

    resp = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": prod.id, "quantity": 1}]},
        headers=auth_headers(creator.id),
    )
    assert resp.status_code == 400
    assert "cannot purchase their own products" in resp.json()["detail"].lower()


def test_order_mixed_currencies_rejected(client: TestClient, db_session: Session):
    """Orders with products having mixed currencies are rejected with HTTP 400."""
    seller = create_test_user(db_session, username="curr_seller")
    buyer = create_test_user(db_session, username="curr_buyer")

    p1 = Product(creator_id=seller.id, type=ProductType.PHYSICAL, title="INR Item", price=100.0, currency="INR", inventory=5)
    p2 = Product(creator_id=seller.id, type=ProductType.PHYSICAL, title="USD Item", price=10.0, currency="USD", inventory=5)
    db_session.add_all([p1, p2])
    db_session.commit()

    resp = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": p1.id, "quantity": 1}, {"product_id": p2.id, "quantity": 1}]},
        headers=auth_headers(buyer.id),
    )
    assert resp.status_code == 400
    assert "same currency" in resp.json()["detail"].lower()


def test_product_currency_normalization_and_validation(client: TestClient, db_session: Session):
    """Product currency is normalized to uppercase and validated against empty values."""
    creator = create_test_user(db_session, username="curr_norm_creator")
    headers = auth_headers(creator.id)

    # 1. Lowercase with whitespace normalizes to uppercase
    resp = client.post(
        "/api/v1/products",
        json={"title": "Norm Currency Product", "price": 50.0, "currency": " usd "},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["currency"] == "USD"
    prod_id = resp.json()["id"]

    # 2. Update currency to EUR
    resp_update = client.patch(
        f"/api/v1/products/{prod_id}",
        json={"currency": " eur "},
        headers=headers,
    )
    assert resp_update.status_code == 200
    assert resp_update.json()["currency"] == "EUR"

    # 3. Update currency with empty string is rejected
    resp_empty = client.patch(
        f"/api/v1/products/{prod_id}",
        json={"currency": "   "},
        headers=headers,
    )
    assert resp_empty.status_code == 422


def test_product_and_order_pagination_page_query(client: TestClient, db_session: Session):
    """Products and orders support 1-indexed page parameter for pagination."""
    seller = create_test_user(db_session, username="page_seller")
    buyer = create_test_user(db_session, username="page_buyer")

    # Create 3 products
    p1 = Product(creator_id=seller.id, type=ProductType.DIGITAL, title="Page Prod 1", price=10.0)
    p2 = Product(creator_id=seller.id, type=ProductType.DIGITAL, title="Page Prod 2", price=20.0)
    p3 = Product(creator_id=seller.id, type=ProductType.DIGITAL, title="Page Prod 3", price=30.0)
    db_session.add_all([p1, p2, p3])
    db_session.commit()

    # Product pagination
    resp_p1 = client.get(f"/api/v1/products?creator_id={seller.id}&page=1&limit=2")
    assert resp_p1.status_code == 200
    assert len(resp_p1.json()) == 2

    resp_p2 = client.get(f"/api/v1/products?creator_id={seller.id}&page=2&limit=2")
    assert resp_p2.status_code == 200
    assert len(resp_p2.json()) == 1

    # Place 3 orders
    client.post("/api/v1/orders", json={"items": [{"product_id": p1.id, "quantity": 1}]}, headers=auth_headers(buyer.id))
    client.post("/api/v1/orders", json={"items": [{"product_id": p2.id, "quantity": 1}]}, headers=auth_headers(buyer.id))
    client.post("/api/v1/orders", json={"items": [{"product_id": p3.id, "quantity": 1}]}, headers=auth_headers(buyer.id))

    # Buyer orders pagination
    resp_my_p1 = client.get("/api/v1/orders/my?page=1&limit=2", headers=auth_headers(buyer.id))
    assert resp_my_p1.status_code == 200
    assert len(resp_my_p1.json()) == 2

    resp_my_p2 = client.get("/api/v1/orders/my?page=2&limit=2", headers=auth_headers(buyer.id))
    assert resp_my_p2.status_code == 200
    assert len(resp_my_p2.json()) == 1

    # Store orders pagination
    resp_store_p1 = client.get("/api/v1/orders/store?page=1&limit=2", headers=auth_headers(seller.id))
    assert resp_store_p1.status_code == 200
    assert len(resp_store_p1.json()) == 2

    resp_store_p2 = client.get("/api/v1/orders/store?page=2&limit=2", headers=auth_headers(seller.id))
    assert resp_store_p2.status_code == 200
    assert len(resp_store_p2.json()) == 1


def test_order_invalid_product_id_whitespace_rejected(client: TestClient, db_session: Session):
    """Empty or whitespace product ID in order items is rejected with HTTP 422."""
    buyer = create_test_user(db_session, username="ws_buyer")
    resp = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": "   ", "quantity": 1}]},
        headers=auth_headers(buyer.id),
    )
    assert resp.status_code == 422


def test_shipped_order_backwards_transition_rejected(client: TestClient, db_session: Session):
    """An order in SHIPPED status cannot be transitioned backwards to PROCESSING or CANCELLED."""
    seller = create_test_user(db_session, username="shipped_guard_seller")
    buyer = create_test_user(db_session, username="shipped_guard_buyer")

    prod = Product(creator_id=seller.id, type=ProductType.PHYSICAL, title="Ship Guard Item", price=100.0, inventory=5)
    db_session.add(prod)
    db_session.commit()

    resp_order = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": prod.id, "quantity": 1}]},
        headers=auth_headers(buyer.id),
    )
    order_id = resp_order.json()["id"]

    # Transition to SHIPPED
    resp_ship = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "SHIPPED"},
        headers=auth_headers(seller.id),
    )
    assert resp_ship.status_code == 200

    # Backwards transition to PROCESSING rejected with 400
    resp_back = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "PROCESSING"},
        headers=auth_headers(seller.id),
    )
    assert resp_back.status_code == 400
    assert "delivered" in resp_back.json()["detail"].lower()

    # Transition to CANCELLED rejected with 400
    resp_cancel = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "CANCELLED"},
        headers=auth_headers(seller.id),
    )
    assert resp_cancel.status_code == 400
    assert "shipped or delivered" in resp_cancel.json()["detail"].lower()


def test_order_from_inactive_seller_rejected(client: TestClient, db_session: Session):
    """Attempting to order products from an inactive or suspended seller returns HTTP 400."""
    seller = create_test_user(db_session, username="inactive_seller_user")
    buyer = create_test_user(db_session, username="buyer_inactive_seller")

    prod = Product(
        creator_id=seller.id,
        type=ProductType.PHYSICAL,
        title="Banned Creator Item",
        price=100.0,
        inventory=5,
        is_active=True,
    )
    db_session.add(prod)
    db_session.commit()

    # Deactivate the seller's account
    seller.is_active = False
    db_session.commit()

    resp = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": prod.id, "quantity": 1}]},
        headers=auth_headers(buyer.id),
    )
    assert resp.status_code == 400
    assert "seller account is not active" in resp.json()["detail"].lower()


def test_update_product_null_images_and_response_serialization(client: TestClient, db_session: Session):
    """Updating product images to null safely normalizes to empty list without raising 500."""
    creator = create_test_user(db_session, username="null_img_creator")
    headers = auth_headers(creator.id)

    prod = Product(
        creator_id=creator.id,
        type=ProductType.PHYSICAL,
        title="Null Images Item",
        price=50.0,
        images=["https://example.com/img.jpg"],
    )
    db_session.add(prod)
    db_session.commit()

    # Patch images with null
    resp = client.patch(
        f"/api/v1/products/{prod.id}",
        json={"images": None},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["images"] == []

    # Get product also serializes images cleanly as []
    resp_get = client.get(f"/api/v1/products/{prod.id}")
    assert resp_get.status_code == 200
    assert resp_get.json()["images"] == []


def test_update_product_type_with_existing_orders_rejected(client: TestClient, db_session: Session):
    """Attempting to alter product type on a product that already has placed orders is rejected with HTTP 400."""
    seller = create_test_user(db_session, username="type_change_seller")
    buyer = create_test_user(db_session, username="type_change_buyer")

    prod = Product(
        creator_id=seller.id,
        type=ProductType.PHYSICAL,
        title="Type Changing Item",
        price=100.0,
        inventory=10,
    )
    db_session.add(prod)
    db_session.commit()

    # Place order
    resp_order = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": prod.id, "quantity": 1}]},
        headers=auth_headers(buyer.id),
    )
    assert resp_order.status_code == 201

    # Attempt to change type from PHYSICAL to DIGITAL
    resp_patch = client.patch(
        f"/api/v1/products/{prod.id}",
        json={"type": "DIGITAL"},
        headers=auth_headers(seller.id),
    )
    assert resp_patch.status_code == 400
    assert "existing orders" in resp_patch.json()["detail"].lower()


def test_cancel_digital_product_order_does_not_alter_inventory(client: TestClient, db_session: Session):
    """Cancelling an order containing digital products marks order CANCELLED and leaves inventory unchanged."""
    seller = create_test_user(db_session, username="dig_cancel_seller")
    buyer = create_test_user(db_session, username="dig_cancel_buyer")

    prod = Product(
        creator_id=seller.id,
        type=ProductType.DIGITAL,
        title="Downloadable Guide",
        price=50.0,
        inventory=0,
    )
    db_session.add(prod)
    db_session.commit()

    resp_order = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": prod.id, "quantity": 2}]},
        headers=auth_headers(buyer.id),
    )
    assert resp_order.status_code == 201
    order_id = resp_order.json()["id"]

    resp_cancel = client.post(
        f"/api/v1/orders/{order_id}/cancel",
        headers=auth_headers(buyer.id),
    )
    assert resp_cancel.status_code == 200
    assert resp_cancel.json()["status"] == "CANCELLED"

    db_session.refresh(prod)
    assert prod.inventory == 0


def test_update_product_whitespace_description_normalized_to_none(client: TestClient, db_session: Session):
    """Updating product with whitespace-only description normalizes it to None."""
    creator = create_test_user(db_session, username="ws_desc_creator")
    headers = auth_headers(creator.id)

    prod = Product(
        creator_id=creator.id,
        type=ProductType.PHYSICAL,
        title="Desc Item",
        description="Initial description",
        price=10.0,
    )
    db_session.add(prod)
    db_session.commit()

    resp = client.patch(
        f"/api/v1/products/{prod.id}",
        json={"description": "   \n\t  "},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["description"] is None


def test_double_inventory_increment_regression_guard(client: TestClient, db_session: Session):
    """Regression test ensuring order cancellation re-credits EXACTLY purchased quantity, never doubling."""
    seller = create_test_user(db_session, username="reg_guard_seller")
    buyer = create_test_user(db_session, username="reg_guard_buyer")

    prod = Product(
        creator_id=seller.id,
        type=ProductType.PHYSICAL,
        title="Regression Guard Shirt",
        price=200.0,
        inventory=10,
    )
    db_session.add(prod)
    db_session.commit()

    # Buy 2 items -> inventory goes from 10 to 8
    resp_order = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": prod.id, "quantity": 2}]},
        headers=auth_headers(buyer.id),
    )
    assert resp_order.status_code == 201
    order_id = resp_order.json()["id"]

    db_session.refresh(prod)
    assert prod.inventory == 8

    # Cancel order -> inventory must be EXACTLY 10 (not 12)
    resp_cancel = client.post(
        f"/api/v1/orders/{order_id}/cancel",
        headers=auth_headers(buyer.id),
    )
    assert resp_cancel.status_code == 200
    assert resp_cancel.json()["status"] == "CANCELLED"

    db_session.refresh(prod)
    assert prod.inventory == 10



