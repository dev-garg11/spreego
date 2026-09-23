from datetime import datetime
from typing import Any, List, Optional
from pydantic import Field, field_validator
from src.models.commerce import OrderStatus, ProductType
from src.validations.auth_schemas import BaseSchema


class CreateProductRequest(BaseSchema):
    type: ProductType = Field(default=ProductType.PHYSICAL, description="Product type")
    title: str = Field(..., max_length=255, description="Product title")
    description: Optional[str] = Field(None, max_length=5000, description="Product description")
    price: float = Field(default=0.0, ge=0.0, description="Product price")
    currency: str = Field(default="INR", max_length=10, description="Currency")
    images: List[str] = Field(default_factory=list, description="List of image URLs")
    inventory: int = Field(default=0, ge=0, description="Stock count")
    is_active: bool = Field(default=True, description="Whether product is active")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Title cannot be empty.")
        return v

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        import math
        if math.isnan(v) or math.isinf(v) or v < 0.0:
            raise ValueError("Price must be a valid non-negative number.")
        return round(float(v), 2)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        if v is not None:
            v = v.strip().upper()
            if not v:
                return "INR"
        return v or "INR"


class UpdateProductRequest(BaseSchema):
    type: Optional[ProductType] = Field(None, description="Updated product type")
    title: Optional[str] = Field(None, max_length=255, description="Updated product title")
    description: Optional[str] = Field(None, max_length=5000, description="Updated description")
    price: Optional[float] = Field(None, ge=0.0, description="Updated price")
    currency: Optional[str] = Field(None, max_length=10, description="Updated currency")
    images: Optional[List[str]] = Field(None, description="Updated images")
    inventory: Optional[int] = Field(None, ge=0, description="Updated inventory")
    is_active: Optional[bool] = Field(None, description="Updated active state")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Title cannot be empty.")
        return v

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            import math
            if math.isnan(v) or math.isinf(v) or v < 0.0:
                raise ValueError("Price must be a valid non-negative number.")
            return round(float(v), 2)
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().upper()
            if not v:
                raise ValueError("Currency cannot be empty.")
        return v


class ProductResponse(BaseSchema):
    id: str
    creator_id: str
    type: ProductType
    title: str
    description: Optional[str] = None
    price: float
    currency: str = "INR"
    images: List[str] = Field(default_factory=list)
    inventory: int = 0
    is_active: bool = True
    is_in_stock: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("images", mode="before")
    @classmethod
    def sanitize_images(cls, v: Any) -> List[str]:
        if v is None:
            return []
        return v


class OrderItemCreate(BaseSchema):
    product_id: str = Field(..., description="ID of the product to order")
    quantity: int = Field(default=1, ge=1, description="Quantity to purchase (must be >= 1)")
    unit_price: Optional[float] = Field(None, description="Client unit price (ignored; server computes price)")
    subtotal: Optional[float] = Field(None, description="Client subtotal (ignored; server computes subtotal)")

    @field_validator("product_id")
    @classmethod
    def validate_product_id(cls, v: str) -> str:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Product ID cannot be empty.")
        return v


class CreateOrderRequest(BaseSchema):
    items: List[OrderItemCreate] = Field(..., min_length=1, description="List of items to order")
    shipping_address: Optional[Any] = Field(None, description="Shipping address (optional for digital/service)")
    total_amount: Optional[float] = Field(None, description="Client total amount (ignored; server calculates total)")


class OrderItemResponse(BaseSchema):
    id: str
    order_id: str
    product_id: str
    quantity: int
    unit_price: float
    subtotal: float
    product: Optional[ProductResponse] = None


class OrderResponse(BaseSchema):
    id: str
    buyer_id: str
    seller_id: str
    total_amount: float
    status: OrderStatus
    shipping_address: Optional[Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    items: List[OrderItemResponse] = Field(default_factory=list)


class UpdateOrderStatusRequest(BaseSchema):
    status: OrderStatus = Field(..., description="New order status")
