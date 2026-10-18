"""Password hashing helpers.

Passwords are never stored in plain text.  The standard-library scrypt
implementation keeps this feature dependency free while using a memory-hard
KDF suitable for account passwords.
"""

import base64
import hashlib
import hmac
import secrets


_SCHEME = "scrypt"
_N = 16_384
_R = 8
_P = 1
_SALT_BYTES = 16
_KEY_BYTES = 64


def hash_password(password: str) -> str:
    if not password or len(password) < 8:
        raise ValueError("Password must contain at least 8 characters.")

    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_N,
        r=_R,
        p=_P,
        dklen=_KEY_BYTES,
    )
    encode = lambda value: base64.urlsafe_b64encode(value).decode("ascii")
    return f"{_SCHEME}${_N}${_R}${_P}${encode(salt)}${encode(digest)}"


def verify_password(password: str, encoded_hash: str | None) -> bool:
    if not password or not encoded_hash:
        return False

    try:
        scheme, n, r, p, salt_value, digest_value = encoded_hash.split("$", 5)
        if scheme != _SCHEME:
            return False
        salt = base64.urlsafe_b64decode(salt_value.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_value.encode("ascii"))
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, UnicodeError):
        return False
