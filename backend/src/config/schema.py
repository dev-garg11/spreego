"""Small additive schema compatibility helpers for local and existing installs."""

from sqlalchemy import inspect, text
from src.config.database import engine


def ensure_auth_columns() -> None:
    """Add password auth columns to an existing users table when needed."""
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    missing_columns = {
        "password_hash": "VARCHAR(255)",
        "failed_login_attempts": "INTEGER NOT NULL DEFAULT 0",
        "locked_until": "TIMESTAMP NULL",
    }
    with engine.begin() as connection:
        for name, definition in missing_columns.items():
            if name not in columns:
                connection.execute(text(f"ALTER TABLE users ADD COLUMN {name} {definition}"))
