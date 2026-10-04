from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.models.violation import ViolationStatusEnum, ViolationSeverityEnum
from app.schemas.evidence import EvidenceRead
from app.schemas.compliance import ComplianceCheckRead


class ViolationBase(BaseModel):
    violation_code: str = Field(min_length=1, max_length=100, description="Short code, e.g. VIOL_MISSING_USP")
    description: str = Field(min_length=1, description="Fact-grounded finding statement")
    severity: ViolationSeverityEnum = Field(default=ViolationSeverityEnum.MAJOR)
    status: ViolationStatusEnum = Field(default=ViolationStatusEnum.FLAGGED_FOR_REVIEW)
    officer_comment: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None


class ViolationCreate(ViolationBase):
    inspection_id: str
    compliance_check_id: Optional[str] = None


class ViolationUpdate(BaseModel):
    description: Optional[str] = None
    severity: Optional[ViolationSeverityEnum] = None
    status: Optional[ViolationStatusEnum] = None
    officer_comment: Optional[str] = None


class ViolationReviewRequest(BaseModel):
    status: ViolationStatusEnum = Field(
        ...,
        description="Target status after officer verification: OFFICER_CONFIRMED or DISMISSED",
    )
    comment: str = Field(
        min_length=3,
        max_length=2000,
        description="Mandatory officer review rationale or evidence justification",
    )


class ViolationRead(ViolationBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    inspection_id: str
    compliance_check_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ViolationDetailRead(ViolationRead):
    evidences: List[EvidenceRead] = []
    compliance_check: Optional[ComplianceCheckRead] = None
