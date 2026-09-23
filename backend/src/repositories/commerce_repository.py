from typing import List, Optional
from sqlalchemy.orm import Session
from src.models.commerce import Order, OrderItem, OrderStatus, Product, ProductType
from src.repositories.base_repository import BaseRepository


class ProductRepository(BaseRepository[Product]):
    def __init__(self, db: Session):
        super().__init__(Product, db)

    def list_products(
        self,
        creator_id: Optional[str] = None,
        product_type: Optional[ProductType] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Product]:
        query = self.db.query(Product)
        if creator_id is not None:
            cid = creator_id.strip()
            if cid:
                query = query.filter(Product.creator_id == cid)
        if product_type is not None:
            query = query.filter(Product.type == product_type)
        if is_active is not None:
            query = query.filter(Product.is_active == is_active)
        return query.order_by(Product.created_at.desc()).offset(skip).limit(limit).all()


class OrderRepository(BaseRepository[Order]):
    def __init__(self, db: Session):
        super().__init__(Order, db)

    def get_orders_for_buyer(
        self,
        buyer_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Order]:
        return (
            self.db.query(Order)
            .filter(Order.buyer_id == buyer_id)
            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_orders_for_seller(
        self,
        seller_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Order]:
        return (
            self.db.query(Order)
            .filter(Order.seller_id == seller_id)
            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
