"""
Operational Analytics and Dashboard API.
Provides database-aggregated metrics, trends, and workload statistics for enforcement officers.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db, require_roles
from app.models.inspection import Inspection, InspectionStatusEnum, OverallResultEnum
from app.models.product import Product
from app.models.user import User
from app.models.violation import Violation, ViolationSeverityEnum, ViolationStatusEnum
from app.schemas.dashboard import (
    CategoryStat,
    DashboardSummaryResponse,
    InspectionTrendPoint,
    InspectorWorkloadStat,
    RecentInspectionSummary,
    RuleViolationStat,
    SeverityStat,
)

router = APIRouter()


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="Get Operational Dashboard Summary",
    description="Returns live database aggregations, compliance trends, and workload statistics.",
)
async def get_dashboard_summary(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Base filter query for inspections
    base_insp_q = select(Inspection)
    if start_date:
        base_insp_q = base_insp_q.where(Inspection.inspection_date >= start_date)
    if end_date:
        base_insp_q = base_insp_q.where(Inspection.inspection_date <= end_date)
    if category:
        base_insp_q = base_insp_q.join(Inspection.product).where(Product.category == category)

    # 1. Inspection Counts
    total_q = select(func.count()).select_from(base_insp_q.subquery())
    total_res = await db.execute(total_q)
    total_inspections = total_res.scalar_one() or 0

    now_utc = datetime.now(timezone.utc)
    today_start = datetime(now_utc.year, now_utc.month, now_utc.day, tzinfo=timezone.utc)
    today_q = select(func.count(Inspection.id)).where(Inspection.inspection_date >= today_start)
    today_res = await db.execute(today_q)
    inspections_today = today_res.scalar_one() or 0

    completed_q = select(func.count(Inspection.id)).where(Inspection.status == InspectionStatusEnum.COMPLETED)
    completed_res = await db.execute(completed_q)
    completed_inspections = completed_res.scalar_one() or 0

    review_req_q = select(func.count(Inspection.id)).where(Inspection.status == InspectionStatusEnum.REVIEW_REQUIRED)
    review_req_res = await db.execute(review_req_q)
    review_required = review_req_res.scalar_one() or 0

    non_comp_q = select(func.count(Inspection.id)).where(
        Inspection.overall_result_placeholder == OverallResultEnum.POTENTIAL_NON_COMPLIANCE
    )
    non_comp_res = await db.execute(non_comp_q)
    potential_non_compliance = non_comp_res.scalar_one() or 0

    reviewed_q = select(func.count(Inspection.id)).where(Inspection.status == InspectionStatusEnum.OFFICER_REVIEWED)
    reviewed_res = await db.execute(reviewed_q)
    officer_reviewed = reviewed_res.scalar_one() or 0

    # 2. Violation Counts
    flagged_viol_q = select(func.count(Violation.id)).where(Violation.status == ViolationStatusEnum.FLAGGED_FOR_REVIEW)
    flagged_res = await db.execute(flagged_viol_q)
    flagged_violations = flagged_res.scalar_one() or 0

    confirmed_viol_q = select(func.count(Violation.id)).where(Violation.status == ViolationStatusEnum.OFFICER_CONFIRMED)
    confirmed_res = await db.execute(confirmed_viol_q)
    officer_confirmed = confirmed_res.scalar_one() or 0

    dismissed_viol_q = select(func.count(Violation.id)).where(Violation.status == ViolationStatusEnum.DISMISSED)
    dismissed_res = await db.execute(dismissed_viol_q)
    dismissed_violations = dismissed_res.scalar_one() or 0

    # Compliance Rate
    comp_q = select(func.count(Inspection.id)).where(
        Inspection.overall_result_placeholder == OverallResultEnum.COMPLIANT
    )
    comp_res = await db.execute(comp_q)
    compliant_count = comp_res.scalar_one() or 0
    compliance_rate = (compliant_count / total_inspections * 100.0) if total_inspections > 0 else 100.0

    # 3. Category Distribution
    cat_q = (
        select(Product.category, func.count(Product.id))
        .group_by(Product.category)
        .order_by(func.count(Product.id).desc())
        .limit(8)
    )
    cat_res = await db.execute(cat_q)
    category_distribution = [
        CategoryStat(category=r[0] or "General", count=r[1])
        for r in cat_res.all()
    ]

    # 4. Violations by Severity
    sev_q = (
        select(Violation.severity, func.count(Violation.id))
        .group_by(Violation.severity)
    )
    sev_res = await db.execute(sev_q)
    violations_by_severity = [
        SeverityStat(
            severity=r[0].value if hasattr(r[0], "value") else str(r[0]),
            count=r[1],
        )
        for r in sev_res.all()
    ]

    # 5. Top Violated Rules
    rule_viol_q = (
        select(Violation.violation_code, func.count(Violation.id))
        .group_by(Violation.violation_code)
        .order_by(func.count(Violation.id).desc())
        .limit(6)
    )
    rule_viol_res = await db.execute(rule_viol_q)
    top_violated_rules = [
        RuleViolationStat(
            rule_code=r[0],
            rule_name=r[0].replace("VIOL_", "").replace("_", " "),
            count=r[1],
        )
        for r in rule_viol_res.all()
    ]

    # 6. Inspector Workload
    inspector_q = (
        select(User.id, User.name, func.count(Inspection.id))
        .outerjoin(Inspection, Inspection.inspector_id == User.id)
        .group_by(User.id, User.name)
        .limit(6)
    )
    inspector_res = await db.execute(inspector_q)
    inspector_workload = [
        InspectorWorkloadStat(
            inspector_id=r[0],
            inspector_name=r[1],
            inspections_count=r[2] or 0,
            pending_reviews=0,
        )
        for r in inspector_res.all()
    ]

    # 7. Recent Inspections
    recent_q = (
        select(Inspection)
        .options(selectinload(Inspection.product), selectinload(Inspection.inspector), selectinload(Inspection.violations))
        .order_by(Inspection.created_at.desc())
        .limit(6)
    )
    recent_res = await db.execute(recent_q)
    recent_items = recent_res.scalars().all()

    recent_inspections = [
        RecentInspectionSummary(
            id=item.id,
            product_name=item.product.name if item.product else "Packaged Commodity",
            brand=item.product.brand if item.product else "N/A",
            inspection_date=item.inspection_date.strftime("%Y-%m-%d %H:%M"),
            status=item.status.value if hasattr(item.status, "value") else str(item.status),
            overall_result=item.overall_result_placeholder.value if hasattr(item.overall_result_placeholder, "value") else str(item.overall_result_placeholder),
            violations_count=len(item.violations),
            inspector_name=item.inspector.name if item.inspector else "Unassigned",
        )
        for item in recent_items
    ]

    # 8. 7-Day Trend
    trend_points: List[InspectionTrendPoint] = []
    for i in range(6, -1, -1):
        day_date = (now_utc - timedelta(days=i)).date()
        day_label = day_date.strftime("%a %d")
        day_start_dt = datetime(day_date.year, day_date.month, day_date.day, tzinfo=timezone.utc)
        day_end_dt = day_start_dt + timedelta(days=1)

        d_q = select(func.count(Inspection.id)).where(
            Inspection.inspection_date >= day_start_dt,
            Inspection.inspection_date < day_end_dt,
        )
        d_res = await db.execute(d_q)
        d_total = d_res.scalar_one() or 0

        trend_points.append(
            InspectionTrendPoint(
                date=day_label,
                total=d_total,
                compliant=d_total,
            )
        )

    return DashboardSummaryResponse(
        total_inspections=total_inspections,
        inspections_today=inspections_today,
        completed_inspections=completed_inspections,
        review_required=review_required,
        potential_non_compliance=potential_non_compliance,
        officer_reviewed=officer_reviewed,
        flagged_violations=flagged_violations,
        officer_confirmed_violations=officer_confirmed,
        dismissed_violations=dismissed_violations,
        compliance_rate=round(compliance_rate, 1),
        category_distribution=category_distribution,
        violations_by_severity=violations_by_severity,
        top_violated_rules=top_violated_rules,
        inspector_workload=inspector_workload,
        recent_inspections=recent_inspections,
        inspection_trend=trend_points,
    )
