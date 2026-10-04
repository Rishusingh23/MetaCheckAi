import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_roles
from app.models.inspection import Inspection
from app.models.report import Report, ReportFormatEnum, ReportStatusEnum, ReportTypeEnum
from app.models.user import RoleEnum, User
from app.schemas.common import PaginatedResponse
from app.schemas.report import ReportCreate, ReportRead
from app.services.reports.export_service import report_service

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[ReportRead],
    summary="List Audit & Inspection Reports",
)
async def list_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    inspection_id: Optional[str] = Query(None),
    report_type: Optional[ReportTypeEnum] = Query(None),
    format_filter: Optional[ReportFormatEnum] = Query(None, alias="format"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Report)

    if inspection_id:
        query = query.where(Report.inspection_id == inspection_id)

    if report_type:
        query = query.where(Report.report_type == report_type)

    if format_filter:
        query = query.where(Report.format == format_filter)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(Report.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedResponse(
        items=[ReportRead.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + len(items)) < total,
    )


@router.post(
    "",
    response_model=ReportRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Report Record",
)
async def create_report(
    report_in: ReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN.value, RoleEnum.ENFORCEMENT_OFFICER.value)),
):
    # Verify inspection exists
    inspection_query = select(Inspection).where(Inspection.id == report_in.inspection_id)
    inspection_result = await db.execute(inspection_query)
    if not inspection_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection with id '{report_in.inspection_id}' not found",
        )

    report = Report(**report_in.model_dump())
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return ReportRead.model_validate(report)


@router.post(
    "/inspections/{inspection_id}/generate",
    response_model=ReportRead,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Advisory Report (PDF/JSON/CSV)",
    description="Assembles complete inspection dossier and renders an immutable statutory advisory report.",
)
async def generate_inspection_report(
    inspection_id: str,
    format: ReportFormatEnum = Query(ReportFormatEnum.PDF, description="Target report format: PDF, JSON, or CSV"),
    report_type: ReportTypeEnum = Query(ReportTypeEnum.INSPECTION_SUMMARY, description="Report type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN.value, RoleEnum.ENFORCEMENT_OFFICER.value)),
):
    try:
        report = await report_service.generate_and_save_report(
            inspection_id=inspection_id,
            report_type=report_type,
            report_format=format,
            generated_by_user_id=current_user.id,
            db=db,
        )
        return ReportRead.model_validate(report)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}",
        )


@router.get(
    "/inspections/{inspection_id}/list",
    response_model=list[ReportRead],
    summary="List Reports for Inspection",
)
async def list_reports_for_inspection(
    inspection_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Report)
        .where(Report.inspection_id == inspection_id)
        .order_by(Report.created_at.desc())
    )
    result = await db.execute(query)
    reports = result.scalars().all()
    return [ReportRead.model_validate(r) for r in reports]


@router.get(
    "/{report_id}",
    response_model=ReportRead,
    summary="Get Report Metadata",
)
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Report).where(Report.id == report_id)
    result = await db.execute(query)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with id '{report_id}' not found",
        )
    return ReportRead.model_validate(report)


@router.get(
    "/{report_id}/download",
    summary="Download Generated Report File",
    description="Streams the immutable report file with appropriate MIME type and Content-Disposition (Authenticated).",
)
async def download_report_file(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Report).where(Report.id == report_id)
    result = await db.execute(query)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with id '{report_id}' not found",
        )

    try:
        content = report_service.read_report_file(report)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    fmt = report.format.value.lower() if hasattr(report.format, "value") else str(report.format).lower()
    filename = os.path.basename(report.file_path) if report.file_path else f"report_{report.id}.{fmt}"

    media_type_map = {
        "pdf": "application/pdf",
        "json": "application/json",
        "csv": "text/csv; charset=utf-8",
    }
    media_type = media_type_map.get(fmt, "application/octet-stream")

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )
