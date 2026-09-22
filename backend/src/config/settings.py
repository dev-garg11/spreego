import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
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


settings = Settings()
