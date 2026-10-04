from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.models.inspection import (
    InspectionStatusEnum,
    InspectionSourceEnum,
    OverallResultEnum,
)
from app.schemas.product import ProductRead
from app.schemas.compliance import ComplianceCheckRead
from app.schemas.violation import ViolationRead
from app.schemas.scan import ScanRead
from app.schemas.history import InspectionHistoryRead


class InspectionBase(BaseModel):
    source_type: InspectionSourceEnum = Field(default=InspectionSourceEnum.PORTAL_UPLOAD)
    notes: Optional[str] = Field(default=None)


class InspectionCreate(InspectionBase):
    product_id: str
    inspector_id: Optional[str] = None
    status: InspectionStatusEnum = Field(default=InspectionStatusEnum.CREATED)
    overall_result_placeholder: OverallResultEnum = Field(default=OverallResultEnum.PENDING_VERIFICATION)
    inspection_date: Optional[datetime] = None


class InspectionUpdate(BaseModel):
    status: Optional[InspectionStatusEnum] = None
    overall_result_placeholder: Optional[OverallResultEnum] = None
    notes: Optional[str] = None
    inspector_id: Optional[str] = None


class InspectionStatusUpdate(BaseModel):
    status: InspectionStatusEnum
    notes: Optional[str] = None
    user_id: Optional[str] = None


class InspectionRead(InspectionBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    product_id: str
    inspector_id: Optional[str] = None
    status: InspectionStatusEnum
    overall_result_placeholder: OverallResultEnum
    inspection_date: datetime
    created_at: datetime
    updated_at: datetime


class InspectionDetailRead(InspectionRead):
    product: Optional[ProductRead] = None
    compliance_checks: List[ComplianceCheckRead] = []
    violations: List[ViolationRead] = []
    scans: List[ScanRead] = []
    history_logs: List[InspectionHistoryRead] = []
