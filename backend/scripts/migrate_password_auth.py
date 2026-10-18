"""Apply the additive password-auth schema update to an existing database."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config.schema import ensure_auth_columns


if __name__ == "__main__":
    ensure_auth_columns()
    print("Password authentication columns are ready.")
