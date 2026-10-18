"""Create the current SQLAlchemy schema in a new Neon PostgreSQL database."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config.database import Base, engine
from src.config.schema import ensure_auth_columns
import src.models  # noqa: F401 - register all models before create_all


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    ensure_auth_columns()
    print("Neon database schema is ready.")
