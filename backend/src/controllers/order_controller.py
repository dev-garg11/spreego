from typing import List
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from src.models.user import User
from src.services.commerce_service import CommerceService
from src.validations.commerce_schemas import (
    CreateOrderRequest,
    OrderResponse,
    UpdateOrderStatusRequest,
)


class OrderController:
    @staticmethod
    def create_order(
        current_user: User,
        payload: CreateOrderRequest,
        db: Session,
    ) -> OrderResponse:
        service = CommerceService(db)
        try:
            order = service.create_order(buyer=current_user, payload=payload)
            return OrderResponse.model_validate(order)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except (ValueError, IntegrityError) as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def get_my_orders(
        current_user: User,
        skip: int,
        limit: int,
        db: Session,
    ) -> List[OrderResponse]:
        service = CommerceService(db)
        orders = service.list_my_orders(buyer_id=current_user.id, skip=skip, limit=limit)
        return [OrderResponse.model_validate(o) for o in orders]

    @staticmethod
    def get_store_orders(
        current_user: User,
        skip: int,
        limit: int,
        db: Session,
    ) -> List[OrderResponse]:
        service = CommerceService(db)
        orders = service.list_seller_orders(seller_id=current_user.id, skip=skip, limit=limit)
        return [OrderResponse.model_validate(o) for o in orders]

    @staticmethod
    def get_order(
        order_id: str,
        current_user: User,
        db: Session,
    ) -> OrderResponse:
        service = CommerceService(db)
        try:
            order = service.get_order(order_id=order_id, current_user=current_user)
            return OrderResponse.model_validate(order)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except PermissionError as err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))

    @staticmethod
    def cancel_order(
        order_id: str,
        current_user: User,
        db: Session,
    ) -> OrderResponse:
        service = CommerceService(db)
        try:
            order = service.cancel_order(order_id=order_id, current_user=current_user)
            return OrderResponse.model_validate(order)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except PermissionError as err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))
        except (ValueError, IntegrityError) as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def update_order_status(
        order_id: str,
        current_user: User,
        payload: UpdateOrderStatusRequest,
        db: Session,
    ) -> OrderResponse:
        service = CommerceService(db)
        try:
            order = service.update_order_status(
                order_id=order_id,
                current_user=current_user,
                new_status=payload.status,
            )
            return OrderResponse.model_validate(order)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except PermissionError as err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))
        except (ValueError, IntegrityError) as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
