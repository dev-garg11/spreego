from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from src.models.commerce import ProductType
from src.models.user import User
from src.services.commerce_service import CommerceService
from src.validations.auth_schemas import MessageResponse
from src.validations.commerce_schemas import (
    CreateProductRequest,
    ProductResponse,
    UpdateProductRequest,
)


class ProductController:
    @staticmethod
    def create_product(
        current_user: User,
        payload: CreateProductRequest,
        db: Session,
    ) -> ProductResponse:
        service = CommerceService(db)
        try:
            product = service.create_product(creator_id=current_user.id, payload=payload)
            return ProductResponse.model_validate(product)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except (ValueError, IntegrityError) as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def get_product(
        product_id: str,
        db: Session,
    ) -> ProductResponse:
        service = CommerceService(db)
        try:
            product = service.get_product(product_id=product_id)
            return ProductResponse.model_validate(product)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))

    @staticmethod
    def update_product(
        product_id: str,
        current_user: User,
        payload: UpdateProductRequest,
        db: Session,
    ) -> ProductResponse:
        service = CommerceService(db)
        try:
            product = service.update_product(
                product_id=product_id,
                current_user=current_user,
                payload=payload,
            )
            return ProductResponse.model_validate(product)
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except PermissionError as err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))
        except (ValueError, IntegrityError) as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def delete_product(
        product_id: str,
        current_user: User,
        db: Session,
    ) -> MessageResponse:
        service = CommerceService(db)
        try:
            service.delete_product(product_id=product_id, current_user=current_user)
            return MessageResponse(message="Product deleted successfully.")
        except LookupError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except PermissionError as err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))
        except (ValueError, IntegrityError) as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @staticmethod
    def list_products(
        creator_id: Optional[str],
        product_type: Optional[ProductType],
        is_active: Optional[bool],
        skip: int,
        limit: int,
        db: Session,
    ) -> List[ProductResponse]:
        service = CommerceService(db)
        products = service.list_products(
            creator_id=creator_id,
            product_type=product_type,
            is_active=is_active,
            skip=skip,
            limit=limit,
        )
        return [ProductResponse.model_validate(p) for p in products]
