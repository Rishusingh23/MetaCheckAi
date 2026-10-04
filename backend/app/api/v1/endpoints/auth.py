"""
Authentication and Session Management Endpoints.
Provides production-grade JWT login, profile retrieval, and token revocation.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.logging import logger
from app.core.security import (
    create_access_token,
    hash_password,
    revoke_token,
    verify_password,
)
from app.models.history import InspectionHistory
from app.models.user import Role, RoleEnum, User
from app.schemas.auth import LoginRequest, LogoutResponse, TokenResponse, UserAuthRead

router = APIRouter()


async def _ensure_default_seed_users(db: AsyncSession) -> None:
    """Ensure standard administrative and officer roles/users exist with bcrypt hashes when demo seeding is enabled."""
    roles_map = {}
    for r in RoleEnum:
        res = await db.execute(select(Role).where(Role.name == r.value))
        role_obj = res.scalar_one_or_none()
        if not role_obj:
            role_obj = Role(name=r.value, description=f"{r.value} Role")
            db.add(role_obj)
            await db.flush()
        roles_map[r.value] = role_obj

    if not (settings.DEMO_SEED_ENABLED or settings.DEMO_DATA_ENABLED) or (settings.ENVIRONMENT == "production" and not settings.DEMO_SEED_ENABLED):
        await db.commit()
        return

    # Seeded demo credentials for development & SIH evaluation only
    default_users = [
        ("admin@metacheck.gov.in", "Administrator", RoleEnum.ADMIN.value, "Admin@123"),
        ("officer@metacheck.gov.in", "Enforcement Officer Verma", RoleEnum.ENFORCEMENT_OFFICER.value, "Officer@123"),
        ("viewer@metacheck.gov.in", "Compliance Auditor", RoleEnum.VIEWER.value, "Viewer@123"),
    ]

    for email, name, role_name, raw_pwd in default_users:
        u_res = await db.execute(select(User).where(User.email == email))
        user = u_res.scalar_one_or_none()
        if not user:
            user = User(
                email=email,
                name=name,
                password_hash=hash_password(raw_pwd),
                role_id=roles_map[role_name].id,
                is_active=True,
            )
            db.add(user)
        else:
            # Upgrade legacy hashes if needed
            if not user.password_hash.startswith("$2b$") and not user.password_hash.startswith("$2a$"):
                user.password_hash = hash_password(raw_pwd)
                db.add(user)

    await db.commit()



@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User Login & JWT Token Generation",
    description="Authenticates officer credentials and issues a signed JWT access token.",
)
async def login(
    login_in: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    # Ensure default accounts are present if fresh DB
    await _ensure_default_seed_users(db)

    query = select(User).options(selectinload(User.role)).where(User.email == login_in.email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"Failed login attempt: unknown email '{login_in.email}'")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(login_in.password, user.password_hash):
        logger.warning(f"Failed login attempt: incorrect password for '{login_in.email}'")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        logger.warning(f"Login blocked: inactive account '{login_in.email}'")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Contact an administrator.",
        )

    role_name = user.role.name if user.role else RoleEnum.VIEWER.value
    token_claims = {
        "email": user.email,
        "name": user.name,
        "role": role_name,
    }
    access_token = create_access_token(subject=user.id, claims=token_claims)

    logger.info(f"User '{user.email}' ({role_name}) logged in successfully.")

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserAuthRead(
            id=user.id,
            name=user.name,
            email=user.email,
            role=role_name,
            is_active=user.is_active,
        ),
    )


@router.get(
    "/me",
    response_model=UserAuthRead,
    summary="Get Current User Profile",
    description="Returns profile information and permissions for the authenticated session.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    role_name = current_user.role.name if current_user.role else RoleEnum.VIEWER.value
    return UserAuthRead(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        role=role_name,
        is_active=current_user.is_active,
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Invalidate Session Token",
    description="Revokes the current JWT access token and logs out user.",
)
async def logout(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    current_user: User = Depends(get_current_user),
):
    token = None
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]

    if token:
        revoke_token(token)

    logger.info(f"User '{current_user.email}' logged out.")
    return LogoutResponse(
        message="Session successfully terminated and token revoked.",
        success=True,
    )
