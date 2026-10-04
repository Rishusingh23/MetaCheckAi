from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db, require_roles
from app.core.security import hash_password
from app.models.user import Role, RoleEnum, User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.user import UserCreate, UserRead, UserUpdate

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[UserRead],
    summary="List Officers & Users",
    description="Retrieve list of officer accounts (ADMIN only).",
)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    role_id: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN.value)),
):
    query = select(User).options(selectinload(User.role))

    if role_id:
        query = query.where(User.role_id == role_id)

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    return PaginatedResponse(
        items=[UserRead.model_validate(u) for u in users],
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + len(users)) < total,
    )


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register Officer User Account",
    description="Register an officer account with bcrypt password hashing (ADMIN only).",
)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN.value)),
):
    # Check if email is unique
    existing_query = select(User).where(User.email == user_in.email)
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email '{user_in.email}' already exists",
        )

    # Check if role exists
    role_query = select(Role).where(Role.id == user_in.role_id)
    role_result = await db.execute(role_query)
    if not role_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with id '{user_in.role_id}' not found",
        )

    user = User(
        name=user_in.name,
        email=user_in.email,
        password_hash=hash_password(user_in.password),
        role_id=user_in.role_id,
        is_active=user_in.is_active,
    )
    db.add(user)
    await db.commit()

    # Load with role
    query = select(User).options(selectinload(User.role)).where(User.id == user.id)
    result = await db.execute(query)
    user_loaded = result.scalar_one()
    return UserRead.model_validate(user_loaded)


@router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Get Officer Profile Details",
)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Allow user to get own profile or ADMIN to inspect any profile
    if current_user.id != user_id and current_user.role and current_user.role.name != RoleEnum.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot view another user's profile details.",
        )

    query = select(User).options(selectinload(User.role)).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id '{user_id}' not found",
        )
    return UserRead.model_validate(user)


@router.put(
    "/{user_id}",
    response_model=UserRead,
    summary="Update User Account",
    description="Update account details or role assignment (ADMIN only).",
)
async def update_user(
    user_id: str,
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN.value)),
):
    query = select(User).options(selectinload(User.role)).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id '{user_id}' not found",
        )

    update_data = user_in.model_dump(exclude_unset=True)
    if "password" in update_data and update_data["password"]:
        user.password_hash = hash_password(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user, attribute_names=["role"])
    return UserRead.model_validate(user)
