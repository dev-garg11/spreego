from typing import Generic, Type, TypeVar, Optional, List
from sqlalchemy.orm import Session
from src.config.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db

    def get_by_id(self, id: str) -> Optional[ModelType]:
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def create(self, entity: ModelType) -> ModelType:
        try:
            self.db.add(entity)
            self.db.commit()
            self.db.refresh(entity)
            return entity
        except Exception:
            self.db.rollback()
            raise

    def update(self, entity: ModelType) -> ModelType:
        try:
            self.db.add(entity)
            self.db.commit()
            self.db.refresh(entity)
            return entity
        except Exception:
            self.db.rollback()
            raise

    def delete(self, entity: ModelType) -> None:
        try:
            self.db.delete(entity)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
