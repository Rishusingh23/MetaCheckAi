from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db, require_roles
from app.models.compliance import ComplianceCheck
from app.models.evidence import Evidence
from app.models.history import InspectionHistory
from app.models.inspection import Inspection, InspectionStatusEnum, OverallResultEnum
from app.models.user import RoleEnum, User
from app.models.violation import (
    Violation,
    ViolationSeverityEnum,
    ViolationStatusEnum,
)
from app.schemas.common import PaginatedResponse
from app.schemas.evidence import EvidenceBase, EvidenceRead
from app.schemas.violation import (
    ViolationCreate,
    ViolationDetailRead,
    ViolationRead,
    ViolationReviewRequest,
    ViolationUpdate,
)

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[ViolationRead],
    summary="List Potential Non-Compliances",
    description="Retrieve flagged violations with severity and status filters.",
)
async def list_violations(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    inspection_id: Optional[str] = Query(None),
    severity: Optional[ViolationSeverityEnum] = Query(None),
    status_filter: Optional[ViolationStatusEnum] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Violation)

    if inspection_id:
        query = query.where(Violation.inspection_id == inspection_id)

    if severity:
        query = query.where(Violation.severity == severity)

    if status_filter:
        query = query.where(Violation.status == status_filter)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(Violation.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedResponse(
        items=[ViolationRead.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + len(items)) < total,
    )


@router.post(
    "",
    response_model=ViolationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Record Potential Non-Compliance Finding",
)
async def create_violation(
    violation_in: ViolationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN.value, RoleEnum.ENFORCEMENT_OFFICER.value)),
):
    # Verify inspection exists
    inspection_query = select(Inspection).where(Inspection.id == violation_in.inspection_id)
    inspection_result = await db.execute(inspection_query)
    if not inspection_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection with id '{violation_in.inspection_id}' not found",
        )

    violation = Violation(**violation_in.model_dump())
    db.add(violation)
    await db.commit()
    await db.refresh(violation)
    return ViolationRead.model_validate(violation)


@router.get(
    "/{violation_id}",
    response_model=ViolationDetailRead,
    summary="Get Violation Details & Evidence",
)
async def get_violation(
    violation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Violation)
        .options(
            selectinload(Violation.evidences),
            selectinload(Violation.compliance_check).selectinload(ComplianceCheck.rule_version),
        )
        .where(Violation.id == violation_id)
    )
    result = await db.execute(query)
    violation = result.scalar_one_or_none()

    if not violation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Violation with id '{violation_id}' not found",
        )
    return ViolationDetailRead.model_validate(violation)


@router.patch(
    "/{violation_id}",
    response_model=ViolationRead,
    summary="Update Violation Status / Severity",
)
async def update_violation(
    violation_id: str,
    violation_in: ViolationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENFORCEMENT_OFFICER")),
):
    query = select(Violation).where(Violation.id == violation_id)
    result = await db.execute(query)
    violation = result.scalar_one_or_none()

    if not violation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Violation with id '{violation_id}' not found",
        )

    for field, value in violation_in.model_dump(exclude_unset=True).items():
        setattr(violation, field, value)

    await db.commit()
    await db.refresh(violation)
    return ViolationRead.model_validate(violation)


@router.patch(
    "/{violation_id}/review",
    response_model=ViolationDetailRead,
    summary="Enforcement Officer Violation Review",
    description="Submit statutory review decision (CONFIRM or DISMISS) with mandatory justification comment.",
)
async def review_violation(
    violation_id: str,
    review_in: ViolationReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENFORCEMENT_OFFICER")),
):
    if review_in.status not in (ViolationStatusEnum.OFFICER_CONFIRMED, ViolationStatusEnum.DISMISSED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid review status '{review_in.status}'. Must be OFFICER_CONFIRMED or DISMISSED.",
        )

    if not review_in.comment or len(review_in.comment.strip()) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mandatory officer comment of at least 3 characters is required for statutory review.",
        )

    query = (
        select(Violation)
        .options(
            selectinload(Violation.evidences),
            selectinload(Violation.compliance_check).selectinload(ComplianceCheck.rule_version),
        )
        .where(Violation.id == violation_id)
    )
    result = await db.execute(query)
    violation = result.scalar_one_or_none()

    if not violation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Violation with id '{violation_id}' not found",
        )

    prev_status = violation.status.value if hasattr(violation.status, "value") else str(violation.status)
    new_status = review_in.status.value if hasattr(review_in.status, "value") else str(review_in.status)

    violation.status = review_in.status
    violation.officer_comment = review_in.comment.strip()
    violation.reviewed_by = current_user.id
    violation.reviewed_at = datetime.utcnow()

    # Log audit entry
    history = InspectionHistory(
        inspection_id=violation.inspection_id,
        user_id=current_user.id,
        action=f"VIOLATION_REVIEWED_{new_status}",
        previous_status=prev_status,
        new_status=new_status,
        change_metadata={
            "violation_id": violation.id,
            "violation_code": violation.violation_code,
            "decision": new_status,
            "officer_comment": violation.officer_comment,
            "officer_name": current_user.name,
        },
    )
    db.add(history)

    # Check inspection violations state
    all_viols_q = select(Violation).where(Violation.inspection_id == violation.inspection_id)
    all_viols_res = await db.execute(all_viols_q)
    all_viols = all_viols_res.scalars().all()

    # Check unreviewed count
    unreviewed = [v for v in all_viols if v.id != violation.id and v.status == ViolationStatusEnum.FLAGGED_FOR_REVIEW]
    insp_q = select(Inspection).where(Inspection.id == violation.inspection_id)
    insp_res = await db.execute(insp_q)
    insp = insp_res.scalar_one_or_none()

    if insp and not unreviewed:
        # All violations reviewed
        insp.status = InspectionStatusEnum.OFFICER_REVIEWED
        # Check if any confirmed
        has_confirmed = any(
            v.status == ViolationStatusEnum.OFFICER_CONFIRMED or (v.id == violation.id and review_in.status == ViolationStatusEnum.OFFICER_CONFIRMED)
            for v in all_viols
        )
        if not has_confirmed:
            insp.overall_result_placeholder = OverallResultEnum.COMPLIANT
        else:
            insp.overall_result_placeholder = OverallResultEnum.POTENTIAL_NON_COMPLIANCE

    await db.commit()
    
    refreshed_q = (
        select(Violation)
        .options(
            selectinload(Violation.evidences),
            selectinload(Violation.compliance_check).selectinload(ComplianceCheck.rule_version),
        )
        .where(Violation.id == violation_id)
    )
    refreshed_res = await db.execute(refreshed_q)
    refreshed_viol = refreshed_res.scalar_one()
    return ViolationDetailRead.model_validate(refreshed_viol)


@router.post(
    "/{violation_id}/evidences",
    response_model=EvidenceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Attach Evidence to Violation",
)
async def add_evidence_to_violation(
    violation_id: str,
    evidence_in: EvidenceBase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN.value, RoleEnum.ENFORCEMENT_OFFICER.value)),
):
    # Verify violation exists
    query = select(Violation).where(Violation.id == violation_id)
    result = await db.execute(query)
    violation = result.scalar_one_or_none()
    if not violation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Violation with id '{violation_id}' not found",
        )

    evidence = Evidence(
        inspection_id=violation.inspection_id,
        violation_id=violation_id,
        **evidence_in.model_dump(),
    )
    db.add(evidence)
    await db.commit()
    await db.refresh(evidence)
    return EvidenceRead.model_validate(evidence)
