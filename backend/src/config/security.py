import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt
from src.config.settings import settings


class TokenError(Exception):
    """Base token exception."""
    pass


class TokenExpiredError(TokenError):
    """Token has expired."""
    pass


class TokenInvalidError(TokenError):
    """Token is invalid or malformed."""
    pass


def create_token(
    payload_data: Dict[str, Any],
    token_type: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT token with type, expiration, and unique jti."""
    to_encode = payload_data.copy()
    now = datetime.now(timezone.utc)
    
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        if token_type == "access":
            expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        elif token_type == "refresh":
            expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        else:
            expire = now + timedelta(minutes=15)

    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": token_type,
        "jti": str(uuid.uuid4()),
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_access_token(user_id: str, extra_data: Optional[Dict[str, Any]] = None) -> str:
    """Create JWT access token for user."""
    payload = {"sub": str(user_id)}
    if extra_data:
        payload.update(extra_data)
    return create_token(payload, token_type="access")


def create_refresh_token(user_id: str, extra_data: Optional[Dict[str, Any]] = None) -> str:
    """Create JWT refresh token for user."""
    payload = {"sub": str(user_id)}
    if extra_data:
        payload.update(extra_data)
    return create_token(payload, token_type="refresh")


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token."""
    if not token or not isinstance(token, str) or not token.strip():
        raise TokenInvalidError("Token must be a non-empty string.")
    try:
        payload = jwt.decode(token.strip(), settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError("Token has expired")
    except (jwt.InvalidTokenError, jwt.PyJWTError) as exc:
        raise TokenInvalidError(f"Invalid token: {str(exc)}")
    except Exception as exc:
        raise TokenInvalidError(f"Invalid token format: {str(exc)}")

