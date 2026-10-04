from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db, require_roles
from app.models.compliance import ComplianceCheck
from app.models.history import InspectionHistory
from app.models.inspection import (
    Inspection,
    InspectionStatusEnum,
    OverallResultEnum,
)
from app.models.product import Product
from app.models.scan import Scan
from app.models.user import RoleEnum, User
from app.models.violation import Violation
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.compliance import (
    EvaluateInspectionRequest,
    InspectionComplianceResponse,
)
from app.schemas.history import InspectionHistoryRead
from app.schemas.inspection import (
    InspectionCreate,
    InspectionDetailRead,
    InspectionRead,
    InspectionStatusUpdate,
    InspectionUpdate,
)
from app.schemas.scan import ScanCreate, ScanRead
from app.schemas.violation import ViolationDetailRead, ViolationRead

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[InspectionRead],
    summary="List Inspections",
    description="Retrieve paginated list of compliance inspections with multi-attribute filtering and search.",
)
async def list_inspections(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search term for product name, brand, barcode/GTIN, or inspection ID"),
    category: Optional[str] = Query(None, description="Filter by product category"),
    status_filter: Optional[InspectionStatusEnum] = Query(None, alias="status"),
    product_id: Optional[str] = Query(None),
    inspector_id: Optional[str] = Query(None),
    result_filter: Optional[OverallResultEnum] = Query(None, alias="overall_result"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Inspection).options(selectinload(Inspection.product)).join(Product, Inspection.product_id == Product.id)

    if search:
        search_filter = or_(
            Inspection.id.ilike(f"%{search}%"),
            Product.name.ilike(f"%{search}%"),
            Product.brand.ilike(f"%{search}%"),
            Product.barcode_gtin.ilike(f"%{search}%"),
            Product.manufacturer.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)

    if category:
        query = query.where(Product.category.ilike(category))

    if status_filter:
        query = query.where(Inspection.status == status_filter)

    if product_id:
        query = query.where(Inspection.product_id == product_id)

    if inspector_id:
        query = query.where(Inspection.inspector_id == inspector_id)

    if result_filter:
        query = query.where(Inspection.overall_result_placeholder == result_filter)

    if start_date:
        query = query.where(Inspection.inspection_date >= start_date)

    if end_date:
        query = query.where(Inspection.inspection_date <= end_date)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(Inspection.inspection_date.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedResponse(
        items=[InspectionRead.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + len(items)) < total,
    )


@router.post(
    "",
    response_model=InspectionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate Inspection",
    description="Create a new compliance inspection record and initialize audit log.",
)
async def create_inspection(
    inspection_in: InspectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN.value, RoleEnum.ENFORCEMENT_OFFICER.value)),
):
    # Verify product exists
    product_query = select(Product).where(Product.id == inspection_in.product_id)
    product_result = await db.execute(product_query)
    if not product_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id '{inspection_in.product_id}' not found",
        )

    insp_data = inspection_in.model_dump()
    if not insp_data.get("inspector_id"):
        insp_data["inspector_id"] = current_user.id

    inspection = Inspection(**insp_data)
    db.add(inspection)
    await db.flush()

    # Create initial audit log
    status_str = inspection.status.value if hasattr(inspection.status, "value") else str(inspection.status)
    source_str = inspection.source_type.value if hasattr(inspection.source_type, "value") else str(inspection.source_type)

    history = InspectionHistory(
        inspection_id=inspection.id,
        user_id=inspection.inspector_id,
        action="INSPECTION_CREATED",
        previous_status=None,
        new_status=status_str,
        change_metadata={"notes": inspection.notes, "source": source_str, "created_by": current_user.name},
    )
    db.add(history)

    await db.commit()
    await db.refresh(inspection)
    return InspectionRead.model_validate(inspection)


@router.get(
    "/{inspection_id}",
    response_model=InspectionDetailRead,
    summary="Get Inspection Detail",
    description="Retrieve inspection dossier with compliance checks, violations, scans, and audit trail.",
)
async def get_inspection(
    inspection_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Inspection)
        .options(
            selectinload(Inspection.product),
            selectinload(Inspection.compliance_checks).selectinload(ComplianceCheck.rule_version),
            selectinload(Inspection.violations).selectinload(Violation.evidences),
            selectinload(Inspection.violations).selectinload(Violation.compliance_check),
            selectinload(Inspection.scans),
            selectinload(Inspection.history_logs),
        )
        .where(Inspection.id == inspection_id)
    )
    result = await db.execute(query)
    inspection = result.scalar_one_or_none()

    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection with id '{inspection_id}' not found",
        )
    return InspectionDetailRead.model_validate(inspection)


@router.patch(
    "/{inspection_id}/status",
    response_model=InspectionRead,
    summary="Update Inspection Status",
    description="Transition inspection status with automatic audit history logging.",
)
async def update_inspection_status(
    inspection_id: str,
    status_in: InspectionStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN.value, RoleEnum.ENFORCEMENT_OFFICER.value)),
):
    query = select(Inspection).where(Inspection.id == inspection_id)
    result = await db.execute(query)
    inspection = result.scalar_one_or_none()

    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection with id '{inspection_id}' not found",
        )

    prev_val = inspection.status.value if hasattr(inspection.status, "value") else str(inspection.status)
    new_val = status_in.status.value if hasattr(status_in.status, "value") else str(status_in.status)

    inspection.status = status_in.status
    if status_in.notes:
        inspection.notes = (inspection.notes or "") + f"\n[Status Update]: {status_in.notes}"

    # Log audit entry
    user_id = status_in.user_id or current_user.id
    history = InspectionHistory(
        inspection_id=inspection.id,
        user_id=user_id,
        action="STATUS_TRANSITION",
        previous_status=prev_val,
        new_status=new_val,
        change_metadata={"notes": status_in.notes, "changed_by": current_user.name},
    )
    db.add(history)

    await db.commit()
    await db.refresh(inspection)
    return InspectionRead.model_validate(inspection)


@router.get(
    "/{inspection_id}/violations",
    response_model=list[ViolationDetailRead],
    summary="Get Inspection Violations & Evidence",
    description="Retrieve all potential non-compliance findings and attached evidence for an inspection.",
)
async def get_inspection_violations(
    inspection_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify inspection exists
    insp_query = select(Inspection).where(Inspection.id == inspection_id)
    insp_res = await db.execute(insp_query)
    if not insp_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection with id '{inspection_id}' not found",
        )

    query = (
        select(Violation)
        .options(
            selectinload(Violation.evidences),
            selectinload(Violation.compliance_check).selectinload(ComplianceCheck.rule_version),
        )
        .where(Violation.inspection_id == inspection_id)
        .order_by(Violation.created_at.asc())
    )
    result = await db.execute(query)
    violations = result.scalars().all()
    return [ViolationDetailRead.model_validate(v) for v in violations]


@router.get(
    "/{inspection_id}/history",
    response_model=list[InspectionHistoryRead],
    summary="Get Inspection Audit Trail",
)
async def get_inspection_history(
    inspection_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(InspectionHistory)
        .where(InspectionHistory.inspection_id == inspection_id)
        .order_by(InspectionHistory.timestamp.asc())
    )
    result = await db.execute(query)
    logs = result.scalars().all()
    return [InspectionHistoryRead.model_validate(log) for log in logs]


@router.post(
    "/{inspection_id}/scans",
    response_model=ScanRead,
    status_code=status.HTTP_201_CREATED,
    summary="Attach Scan Record",
)
async def add_scan_to_inspection(
    inspection_id: str,
    scan_in: ScanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN.value, RoleEnum.ENFORCEMENT_OFFICER.value)),
):
    # Verify inspection exists
    query = select(Inspection).where(Inspection.id == inspection_id)
    result = await db.execute(query)
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection with id '{inspection_id}' not found",
        )

    scan = Scan(
        inspection_id=inspection_id,
        image_path=scan_in.image_path,
        panel_type=scan_in.panel_type,
        processing_status=scan_in.processing_status,
        product_image_id=scan_in.product_image_id,
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    return ScanRead.model_validate(scan)


@router.post(
    "/{inspection_id}/evaluate",
    response_model=InspectionComplianceResponse,
    summary="Evaluate Legal Metrology Compliance",
    description="Executes the version-aware Legal Metrology Rule Engine against extracted commodity declarations.",
)
async def evaluate_inspection_compliance(
    inspection_id: str,
    payload: Optional[EvaluateInspectionRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN.value, RoleEnum.ENFORCEMENT_OFFICER.value)),
):
    from app.services.rules import rule_engine

    try:
        user_id = payload.user_id if payload else current_user.id
        result = await rule_engine.evaluate_inspection(
            inspection_id=inspection_id,
            db=db,
            user_id=user_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Compliance evaluation failed: {str(e)}",
        )


@router.get(
    "/{inspection_id}/compliance",
    response_model=InspectionComplianceResponse,
    summary="Get Inspection Compliance Dossier",
    description="Retrieve existing Legal Metrology compliance checks, findings, and evidence for an inspection.",
)
async def get_inspection_compliance_dossier(
    inspection_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.rules import rule_engine

    try:
        result = await rule_engine.get_inspection_compliance(
            inspection_id=inspection_id,
            db=db,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve compliance dossier: {str(e)}",
        )
