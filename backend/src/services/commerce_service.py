from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from src.models.commerce import Order, OrderItem, OrderStatus, Product, ProductType
from src.models.user import User
from src.repositories.commerce_repository import OrderRepository, ProductRepository
from src.repositories.user_repository import UserRepository
from src.validations.commerce_schemas import (
    CreateOrderRequest,
    CreateProductRequest,
    UpdateProductRequest,
)


class CommerceService:
    def __init__(self, db: Session):
        self.db = db
        self.product_repo = ProductRepository(db)
        self.order_repo = OrderRepository(db)
        self.user_repo = UserRepository(db)

    # =========================================================================
    # Product Operations
    # =========================================================================

    def create_product(self, creator_id: str, payload: CreateProductRequest) -> Product:
        creator = self.user_repo.get_by_id(creator_id)
        if not creator or not creator.is_active:
            raise LookupError("User not found.")

        title = payload.title.strip()
        if not title:
            raise ValueError("Title cannot be empty.")

        price = float(payload.price)
        if price < 0.0:
            raise ValueError("Price cannot be negative.")

        inventory = int(payload.inventory) if payload.inventory is not None else 0
        if inventory < 0:
            raise ValueError("Inventory cannot be negative.")

        product = Product(
            creator_id=creator.id,
            type=payload.type,
            title=title,
            description=payload.description.strip() if payload.description and payload.description.strip() else None,
            price=price,
            currency=payload.currency.strip().upper() if payload.currency and payload.currency.strip() else "INR",
            images=payload.images if payload.images is not None else [],
            inventory=inventory,
            is_active=payload.is_active if payload.is_active is not None else True,
        )
        return self.product_repo.create(product)

    def get_product(self, product_id: str) -> Product:
        product = self.product_repo.get_by_id(product_id)
        if not product:
            raise LookupError("Product not found.")
        return product

    def update_product(
        self,
        product_id: str,
        current_user: User,
        payload: UpdateProductRequest,
    ) -> Product:
        product = self.product_repo.get_by_id(product_id)
        if not product:
            raise LookupError("Product not found.")

        # Strict ownership check: current_user.id == product.creator_id, returns 403 on non-owners
        if product.creator_id != current_user.id:
            raise PermissionError("You do not have permission to update this product.")

        update_data = payload.model_dump(exclude_unset=True)

        if "title" in update_data:
            val = update_data["title"]
            if val is None or not str(val).strip():
                raise ValueError("Title cannot be empty.")
            update_data["title"] = str(val).strip()

        if "price" in update_data:
            val = update_data["price"]
            if val is not None and float(val) < 0.0:
                raise ValueError("Price cannot be negative.")

        if "currency" in update_data:
            val = update_data["currency"]
            if val is not None:
                stripped = str(val).strip().upper()
                if not stripped:
                    raise ValueError("Currency cannot be empty.")
                update_data["currency"] = stripped

        if "inventory" in update_data:
            val = update_data["inventory"]
            if val is not None and int(val) < 0:
                raise ValueError("Inventory cannot be negative.")

        if "description" in update_data:
            val = update_data["description"]
            update_data["description"] = val.strip() if val and str(val).strip() else None

        if "images" in update_data:
            val = update_data["images"]
            update_data["images"] = val if val is not None else []

        if "type" in update_data and update_data["type"] != product.type:
            has_orders = (
                self.db.query(OrderItem).filter(OrderItem.product_id == product.id).first()
                is not None
            )
            if has_orders:
                raise ValueError("Cannot change product type for a product with existing orders.")

        ALLOWED_FIELDS = {
            "title",
            "description",
            "price",
            "currency",
            "images",
            "inventory",
            "is_active",
            "type",
        }
        for field, value in update_data.items():
            if field in ALLOWED_FIELDS:
                setattr(product, field, value)

        product.updated_at = datetime.now(timezone.utc)
        return self.product_repo.update(product)

    def delete_product(self, product_id: str, current_user: User) -> None:
        product = self.product_repo.get_by_id(product_id)
        if not product:
            raise LookupError("Product not found.")

        # Strict ownership check: current_user.id == product.creator_id, returns 403 on non-owners
        if product.creator_id != current_user.id:
            raise PermissionError("You do not have permission to delete this product.")

        # Prevent deletion if orders exist for this product
        has_orders = (
            self.db.query(OrderItem).filter(OrderItem.product_id == product.id).first()
            is not None
        )
        if has_orders:
            raise ValueError(
                "Cannot delete product with existing orders. Please deactivate the product (set is_active=False) instead."
            )

        self.product_repo.delete(product)

    def list_products(
        self,
        creator_id: Optional[str] = None,
        product_type: Optional[ProductType] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Product]:
        return self.product_repo.list_products(
            creator_id=creator_id,
            product_type=product_type,
            is_active=is_active,
            skip=skip,
            limit=limit,
        )

    # =========================================================================
    # Order Operations
    # =========================================================================

    def create_order(self, buyer: User, payload: CreateOrderRequest) -> Order:
        if not buyer or not buyer.is_active:
            raise LookupError("User not found.")

        if not payload.items:
            raise ValueError("Order must contain at least one item.")

        fetched_products: List[Product] = []
        for item in payload.items:
            if item.quantity < 1:
                raise ValueError("Item quantity must be at least 1.")

            product = self.product_repo.get_by_id(item.product_id)
            if not product:
                raise LookupError(f"Product '{item.product_id}' not found.")
            if not product.is_active:
                raise ValueError(f"Product '{product.title}' is not active.")

            # Validate stock inventory (fails with HTTP 400 if quantity exceeds available inventory)
            if product.type == ProductType.PHYSICAL and product.inventory < item.quantity:
                raise ValueError(
                    f"Insufficient stock for product '{product.title}'. Requested: {item.quantity}, available: {product.inventory}."
                )

            fetched_products.append(product)

        # Enforce consistent seller per order
        sellers = {p.creator_id for p in fetched_products}
        if len(sellers) > 1:
            raise ValueError("All products in an order must belong to the same seller.")
        seller_id = next(iter(sellers))

        # Check self-purchase: buyers cannot buy their own products
        if seller_id == buyer.id:
            raise ValueError("Buyers cannot purchase their own products.")

        # Check seller account is active
        seller = self.user_repo.get_by_id(seller_id)
        if not seller or not seller.is_active:
            raise ValueError("Seller account is not active.")

        # Check consistent currency across all products in the order
        currencies = {p.currency for p in fetched_products}
        if len(currencies) > 1:
            raise ValueError("All products in an order must have the same currency.")

        # Check stock against aggregated quantities per product to prevent duplicate item underflow
        # ponytail: transaction-level stock validation; upgrade to SELECT FOR UPDATE or Redis lock for flash sales
        requested_quantities: dict = {}
        for item in payload.items:
            requested_quantities[item.product_id] = (
                requested_quantities.get(item.product_id, 0) + item.quantity
            )

        for product in fetched_products:
            total_qty = requested_quantities[product.id]
            if product.type == ProductType.PHYSICAL and product.inventory < total_qty:
                raise ValueError(
                    f"Insufficient stock for product '{product.title}'. Requested: {total_qty}, available: {product.inventory}."
                )

        # Server-calculated pricing & stock decrement (client prices never trusted)
        total_amount = 0.0
        order_items: List[OrderItem] = []

        try:
            for item_input, product in zip(payload.items, fetched_products):
                unit_price = float(product.price)
                subtotal = round(unit_price * item_input.quantity, 2)
                total_amount += subtotal

                # Decrement inventory upon successful order creation for physical products
                if product.type == ProductType.PHYSICAL:
                    product.inventory -= item_input.quantity
                    self.db.add(product)

                order_items.append(
                    OrderItem(
                        product_id=product.id,
                        quantity=item_input.quantity,
                        unit_price=unit_price,
                        subtotal=subtotal,
                    )
                )

            total_amount = round(total_amount, 2)

            order = Order(
                buyer_id=buyer.id,
                seller_id=seller_id,
                total_amount=total_amount,
                status=OrderStatus.CREATED,
                shipping_address=payload.shipping_address,
                items=order_items,
            )
            self.db.add(order)
            self.db.commit()
            self.db.refresh(order)
            return order
        except Exception:
            self.db.rollback()
            raise

    def get_order(self, order_id: str, current_user: User) -> Order:
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise LookupError("Order not found.")

        # Accessible only to buyer or seller
        if order.buyer_id != current_user.id and order.seller_id != current_user.id:
            raise PermissionError("You do not have permission to view this order.")

        return order

    def list_my_orders(
        self,
        buyer_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Order]:
        return self.order_repo.get_orders_for_buyer(buyer_id=buyer_id, skip=skip, limit=limit)

    def list_seller_orders(
        self,
        seller_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Order]:
        return self.order_repo.get_orders_for_seller(seller_id=seller_id, skip=skip, limit=limit)

    def cancel_order(self, order_id: str, current_user: User) -> Order:
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise LookupError("Order not found.")

        # Accessible only to buyer or seller
        if order.buyer_id != current_user.id and order.seller_id != current_user.id:
            raise PermissionError("You do not have permission to cancel this order.")

        if order.status == OrderStatus.CANCELLED:
            raise ValueError("Order is already cancelled.")

        if order.status in (OrderStatus.SHIPPED, OrderStatus.DELIVERED):
            raise ValueError("Cannot cancel order that has already been shipped or delivered.")

        try:
            # Re-credits inventory if cancelled before shipping
            for item in order.items:
                prod = item.product or self.product_repo.get_by_id(item.product_id)
                if prod and prod.type == ProductType.PHYSICAL:
                    prod.inventory += item.quantity
                    self.db.add(prod)

            order.status = OrderStatus.CANCELLED
            order.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(order)
            return order
        except Exception:
            self.db.rollback()
            raise

    def update_order_status(
        self,
        order_id: str,
        current_user: User,
        new_status: OrderStatus,
    ) -> Order:
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise LookupError("Order not found.")

        # Only seller can update order status
        if order.seller_id != current_user.id:
            raise PermissionError("Only the store owner/seller can update order status.")

        if order.status == OrderStatus.CANCELLED:
            raise ValueError("Cannot update status of a cancelled order.")

        if order.status == OrderStatus.DELIVERED:
            raise ValueError("Cannot update status of an already delivered order.")

        if new_status == OrderStatus.CANCELLED:
            # Delegate to cancel_order so inventory is properly re-credited
            return self.cancel_order(order_id=order_id, current_user=current_user)

        if order.status == new_status:
            return order

        if order.status == OrderStatus.SHIPPED and new_status != OrderStatus.DELIVERED:
            raise ValueError("A shipped order can only be transitioned to DELIVERED.")

        order.status = new_status
        order.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(order)
        return order
