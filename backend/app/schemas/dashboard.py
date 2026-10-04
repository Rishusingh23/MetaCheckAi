from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class InspectionTrendPoint(BaseModel):
    date: str = Field(description="Date label, e.g. 2026-09-15 or Day name")
    total: int = 0
    compliant: int = 0
    review_required: int = 0
    potential_non_compliance: int = 0
    officer_reviewed: int = 0


class CategoryStat(BaseModel):
    category: str
    count: int


class SeverityStat(BaseModel):
    severity: str
    count: int


class RuleViolationStat(BaseModel):
    rule_code: str
    rule_name: str
    count: int
    critical_count: int = 0


class InspectorWorkloadStat(BaseModel):
    inspector_id: Optional[str] = None
    inspector_name: str
    inspections_count: int
    pending_reviews: int


class RecentInspectionSummary(BaseModel):
    id: str
    product_name: str
    brand: str
    inspection_date: str
    status: str
    overall_result: str
    violations_count: int
    inspector_name: Optional[str] = None


class DashboardSummaryResponse(BaseModel):
    total_inspections: int
    inspections_today: int
    completed_inspections: int
    review_required: int
    potential_non_compliance: int
    officer_reviewed: int
    flagged_violations: int
    officer_confirmed_violations: int
    dismissed_violations: int
    compliance_rate: float
    inspection_trend: List[InspectionTrendPoint] = []
    category_distribution: List[CategoryStat] = []
    violations_by_severity: List[SeverityStat] = []
    top_violated_rules: List[RuleViolationStat] = []
    inspector_workload: List[InspectorWorkloadStat] = []
    recent_inspections: List[RecentInspectionSummary] = []
