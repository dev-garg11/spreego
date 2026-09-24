import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "SPREEGO Authentication API")
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://spreego_user:spreego_pass@localhost:5432/spreego_db"
    )
    
    # JWT Security
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY", 
        "spreego_super_secret_jwt_key_at_least_32_characters_long_2026"
    )
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    # OTP Configuration
    OTP_EXPIRE_MINUTES: int = int(os.getenv("OTP_EXPIRE_MINUTES", "5"))
    OTP_LENGTH: int = int(os.getenv("OTP_LENGTH", "6"))
    MAX_OTP_ATTEMPTS: int = int(os.getenv("MAX_OTP_ATTEMPTS", "5"))

    # Phase 10: Creator Memberships Feature Toggle
    ENABLE_PAID_MEMBERSHIPS: bool = os.getenv("ENABLE_PAID_MEMBERSHIPS", "false").lower() in ("true", "1", "yes")

    # Phase 3: Media Upload Infrastructure Configuration
    STORAGE_PROVIDER: str = os.getenv("STORAGE_PROVIDER", "local")
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")
    MAX_IMAGE_SIZE_BYTES: int = int(os.getenv("MAX_IMAGE_SIZE_BYTES", str(15 * 1024 * 1024)))  # 15 MB
    MAX_VIDEO_SIZE_BYTES: int = int(os.getenv("MAX_VIDEO_SIZE_BYTES", str(250 * 1024 * 1024)))  # 250 MB


settings = Settings()
