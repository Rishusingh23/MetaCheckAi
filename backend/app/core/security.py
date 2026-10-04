"""
Security and Cryptography Utilities for MetaCheck AI.
Provides industry-standard bcrypt password hashing with independent salt per entry,
JWT access token generation with issuer/audience claims, cryptographic signature verification,
and session token revocation management.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Set
import bcrypt
import jwt
from app.core.config import settings
from app.core.logging import logger

# In-memory token revocation blocklist (can be backed by Redis in clustered production)
_REVOKED_TOKENS: Set[str] = set()


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt with standard cost factor (12 rounds).
    Each call generates an independent cryptographically secure salt.
    """
    if not password:
        raise ValueError("Password cannot be empty")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash using bcrypt.checkpw.
    Returns False immediately if hash is missing, malformed, or invalid.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        # Standard bcrypt Modular Crypt Format starts with $2a$, $2b$, or $2y$
        if not (hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$") or hashed_password.startswith("$2y$")):
            return False
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def create_access_token(
    subject: str,
    claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a signed JWT access token with user ID subject, issuer, audience, and expiration.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: Dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }

    if claims:
        payload.update(claims)

    encoded_jwt = jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT access token.
    Validates signature, expiration, issuer, audience, and checks revocation blocklist.
    Returns payload dictionary if valid, or None if invalid/expired/revoked.
    """
    if not token or is_token_revoked(token):
        return None
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
            options={
                "verify_exp": True,
                "verify_sub": True,
                "verify_iss": True,
                "verify_aud": True,
            },
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.debug("JWT token signature has expired.")
        return None
    except jwt.PyJWTError:
        logger.debug("Invalid JWT token received.")
        return None


def revoke_token(token: str) -> None:
    """
    Mark a JWT access token as revoked (blacklisted on logout).
    """
    if token:
        _REVOKED_TOKENS.add(token)
        logger.info("Access token added to revocation blocklist.")


def is_token_revoked(token: str) -> bool:
    """
    Check whether a given JWT access token is in the revocation blocklist.
    """
    return token in _REVOKED_TOKENS


__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "revoke_token",
    "is_token_revoked",
]

