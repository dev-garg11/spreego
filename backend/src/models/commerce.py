import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import backref, relationship
from src.config.database import Base


class ProductType(str, enum.Enum):
    PHYSICAL = "PHYSICAL"
    DIGITAL = "DIGITAL"
    AFFILIATE = "AFFILIATE"
    SERVICE = "SERVICE"


class OrderStatus(str, enum.Enum):
    CREATED = "CREATED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAID = "PAID"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class Product(Base):
    __tablename__ = "products"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    creator_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type = Column(
        SAEnum(
            ProductType,
            name="product_type",
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=ProductType.PHYSICAL,
        server_default=ProductType.PHYSICAL.value,
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, default=0.0, server_default="0.0", nullable=False)
    currency = Column(String(10), default="INR", server_default="INR", nullable=False)
    images = Column(JSON, nullable=False, default=list)
    inventory = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
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
    creator = relationship(
        "User",
        backref=backref("products", cascade="all, delete-orphan", passive_deletes=True),
    )
    order_items = relationship(
        "OrderItem",
        back_populates="product",
    )

    @property
    def is_in_stock(self) -> bool:
        if self.type == ProductType.PHYSICAL:
            return self.inventory > 0
        return True

    def __repr__(self) -> str:
        return f"<Product(id='{self.id}', title='{self.title}', type='{self.type}', price={self.price})>"


class Order(Base):
    __tablename__ = "orders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    buyer_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seller_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    total_amount = Column(Float, default=0.0, server_default="0.0", nullable=False)
    status = Column(
        SAEnum(
            OrderStatus,
            name="order_status",
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=OrderStatus.CREATED,
        server_default=OrderStatus.CREATED.value,
        nullable=False,
        index=True,
    )
    shipping_address = Column(JSON, nullable=True)
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
    buyer = relationship(
        "User",
        foreign_keys=[buyer_id],
        backref=backref("orders_as_buyer", cascade="all, delete-orphan", passive_deletes=True),
    )
    seller = relationship(
        "User",
        foreign_keys=[seller_id],
        backref=backref("orders_as_seller", cascade="all, delete-orphan", passive_deletes=True),
    )
    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Order(id='{self.id}', buyer_id='{self.buyer_id}', seller_id='{self.seller_id}', total={self.total_amount}, status='{self.status}')>"


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    order_id = Column(
        String(36),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id = Column(
        String(36),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items", lazy="joined")

    def __repr__(self) -> str:
        return f"<OrderItem(id='{self.id}', order_id='{self.order_id}', product_id='{self.product_id}', qty={self.quantity}, subtotal={self.subtotal})>"
