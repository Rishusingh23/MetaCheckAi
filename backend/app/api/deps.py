"""
Dependency injection module for FastAPI.
Provides database sessions, authenticated user context from cryptographically verified JWT tokens,
and strict RBAC role enforcement.

Security Guarantee:
- No X-User-Id or X-User-Role authentication bypass.
- No automatic fallback to ADMIN.
- Strict Authorization: Bearer <JWT> validation with signature, expiration, issuer, audience,
  subject lookup, and active user verification.
"""
from typing import Callable, Optional
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User


async def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Resolve and validate current authenticated user context strictly from signed JWT access tokens.
    Requires: 'Authorization: Bearer <jwt>'.
    Rejects missing, malformed, expired, revoked, or unverified tokens with HTTP 401.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or revoked access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload["sub"]

    query = (
        select(User)
        .options(selectinload(User.role))
        .where((User.id == user_id) | (User.email == user_id))
    )
    res = await db.execute(query)
    user = res.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authenticated user '{user_id}' not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )

    return user


def require_roles(*allowed_roles: str) -> Callable:
    """
    Enforces that the current authenticated user has one of the allowed roles.
    Raises HTTP 403 FORBIDDEN if the user's role is not authorized.
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_role = current_user.role.name if current_user.role else ""
        if user_role not in allowed_roles and "*" not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: role '{user_role}' lacks required permissions. Required: {', '.join(allowed_roles)}",
            )
        return current_user

    return role_checker
