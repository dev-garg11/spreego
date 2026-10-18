from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from src.config.settings import settings

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
    future=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI Dependency for database session injection."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
