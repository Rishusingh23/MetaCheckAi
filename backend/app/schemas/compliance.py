from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.compliance import ComplianceStatusEnum
from app.schemas.rule import RuleVersionRead


class ComplianceCheckBase(BaseModel):
    status: ComplianceStatusEnum = Field(default=ComplianceStatusEnum.REVIEW, description="Screening outcome")
    explanation: Optional[str] = Field(default=None, description="Detailed rationale for screening status")
    detected_value: Optional[str] = Field(default=None)
    expected_requirement: Optional[str] = Field(default=None)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    severity: Optional[str] = Field(default=None)


class ComplianceCheckCreate(ComplianceCheckBase):
    inspection_id: str
    rule_version_id: str


class ComplianceCheckRead(ComplianceCheckBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    inspection_id: str
    rule_version_id: str
    created_at: datetime
    rule_version: Optional[RuleVersionRead] = None


class ComplianceCheckDetailRead(ComplianceCheckRead):
    violations: List[Dict[str, Any]] = []


class EvaluateInspectionRequest(BaseModel):
    user_id: Optional[str] = Field(default=None, description="Evaluating officer ID")
    notes: Optional[str] = Field(default=None, description="Optional evaluation notes")


class InspectionComplianceResponse(BaseModel):
    inspection_id: str
    overall_status: str
    total_rules_evaluated: int
    pass_count: int
    fail_count: int
    review_count: int
    not_applicable_count: int
    violations_flagged: int
    mean_confidence: float
    screening_score: Optional[float] = 100.0
    checks: List[ComplianceCheckRead]
    disclaimer: str = (
        "MetaCheck AI operates as an AI-assisted screening tool. Output findings represent "
        "advisory indications. Final legal compliance determinations rest exclusively with "
        "authorized Legal Metrology Officers."
    )

