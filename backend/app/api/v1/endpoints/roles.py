from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_roles
from app.models.user import Role, RoleEnum, User
from app.schemas.role import RoleCreate, RoleRead

router = APIRouter()


@router.get(
    "",
    response_model=List[RoleRead],
    summary="List RBAC Roles",
)
async def list_roles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Role).order_by(Role.name.asc())
    result = await db.execute(query)
    roles = result.scalars().all()
    return [RoleRead.model_validate(r) for r in roles]


@router.post(
    "",
    response_model=RoleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create RBAC Role",
)
async def create_role(
    role_in: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN.value)),
):
    query = select(Role).where(Role.name == role_in.name)
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Role '{role_in.name}' already exists",
        )

    role = Role(**role_in.model_dump())
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return RoleRead.model_validate(role)
