from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db, require_roles
from app.models.rule import Rule, RuleVersion
from app.models.user import RoleEnum, User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.rule import (
    RuleCreate,
    RuleDetailRead,
    RuleRead,
    RuleUpdate,
    RuleVersionBase,
    RuleVersionCreate,
    RuleVersionRead,
)

router = APIRouter()


class RuleVersionStatusUpdate(BaseModel):
    is_active: Optional[bool] = None
    active_from: Optional[datetime] = None
    active_to: Optional[datetime] = None
    source_gazette_reference: Optional[str] = None


@router.get(
    "",
    response_model=PaginatedResponse[RuleRead],
    summary="List Statutory Rules",
    description="Retrieve list of Legal Metrology statutory rules.",
)
async def list_rules(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Rule)
    if is_active is not None:
        query = query.where(Rule.is_active == is_active)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(Rule.rule_code.asc()).offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedResponse(
        items=[RuleRead.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + len(items)) < total,
    )


@router.post(
    "",
    response_model=RuleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register Statutory Rule",
    description="Register a new Legal Metrology statutory rule (ADMIN only).",
)
async def create_rule(
    rule_in: RuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN.value)),
):
    existing_query = select(Rule).where(Rule.rule_code == rule_in.rule_code)
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Rule with code '{rule_in.rule_code}' already exists",
        )

    rule = Rule(**rule_in.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return RuleRead.model_validate(rule)


@router.get(
    "/{rule_id}",
    response_model=RuleDetailRead,
    summary="Get Rule Details with Version History",
)
async def get_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Rule).options(selectinload(Rule.versions)).where(Rule.id == rule_id)
    result = await db.execute(query)
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule with id '{rule_id}' not found",
        )
    return RuleDetailRead.model_validate(rule)


@router.put(
    "/{rule_id}",
    response_model=RuleRead,
    summary="Update Rule Metadata",
    description="Update administrative description and title of a rule (ADMIN only).",
)
async def update_rule(
    rule_id: str,
    rule_in: RuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN.value)),
):
    query = select(Rule).where(Rule.id == rule_id)
    result = await db.execute(query)
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule with id '{rule_id}' not found",
        )

    for field, value in rule_in.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)

    await db.commit()
    await db.refresh(rule)
    return RuleRead.model_validate(rule)


@router.get(
    "/{rule_id}/versions",
    response_model=List[RuleVersionRead],
    summary="List Versions for Rule",
)
async def list_rule_versions(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(RuleVersion).where(RuleVersion.rule_id == rule_id).order_by(RuleVersion.created_at.desc())
    result = await db.execute(query)
    versions = result.scalars().all()
    return [RuleVersionRead.model_validate(v) for v in versions]


@router.post(
    "/{rule_id}/versions",
    response_model=RuleVersionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Publish New Immutable Rule Version",
    description="Publishes a new statutory version without mutating historical versions (ADMIN only).",
)
async def create_rule_version(
    rule_id: str,
    version_in: RuleVersionBase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN.value)),
):
    rule_query = select(Rule).where(Rule.id == rule_id)
    rule_result = await db.execute(rule_query)
    if not rule_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule with id '{rule_id}' not found",
        )

    # Check if this version label already exists for this rule
    existing_ver = select(RuleVersion).where(
        RuleVersion.rule_id == rule_id,
        RuleVersion.version == version_in.version,
    )
    ver_res = await db.execute(existing_ver)
    if ver_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Version '{version_in.version}' already exists for this rule. Create a new version identifier.",
        )

    rule_version = RuleVersion(rule_id=rule_id, **version_in.model_dump())
    db.add(rule_version)
    await db.commit()
    await db.refresh(rule_version)
    return RuleVersionRead.model_validate(rule_version)


@router.patch(
    "/{rule_id}/versions/{version_id}/status",
    response_model=RuleVersionRead,
    summary="Update Rule Version Temporal Lifecycle",
    description="Adjust active date bounds or gazette reference of an existing version (ADMIN only).",
)
async def update_rule_version_status(
    rule_id: str,
    version_id: str,
    status_in: RuleVersionStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN.value)),
):
    query = select(RuleVersion).where(
        RuleVersion.id == version_id,
        RuleVersion.rule_id == rule_id,
    )
    result = await db.execute(query)
    version_obj = result.scalar_one_or_none()

    if not version_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule version '{version_id}' not found for rule '{rule_id}'",
        )

    if status_in.active_from is not None:
        version_obj.active_from = status_in.active_from
    if status_in.active_to is not None:
        version_obj.active_to = status_in.active_to
    if status_in.source_gazette_reference is not None:
        version_obj.source_gazette_reference = status_in.source_gazette_reference

    await db.commit()
    await db.refresh(version_obj)
    return RuleVersionRead.model_validate(version_obj)


@router.post(
    "/seed-baseline",
    response_model=MessageResponse,
    summary="Seed Statutory Baseline Rules",
    description="Initializes or updates authoritative PCR 2011 Legal Metrology rules and versions (ADMIN only).",
)
async def seed_rules_baseline(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN.value)),
):
    from app.services.rules import seed_statutory_baseline_rules

    seeded_count = await seed_statutory_baseline_rules(db)
    return MessageResponse(
        message=f"Successfully seeded/verified {seeded_count} statutory baseline rules and versions."
    )
