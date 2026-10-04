from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.declaration import DeclarationTypeEnum, ExtractionStatusEnum


class DeclarationItemSchema(BaseModel):
    id: str
    scan_id: str
    declaration_type: DeclarationTypeEnum
    raw_value: str
    normalized_value: Optional[str] = None
    confidence: Optional[float] = None
    source_text: Optional[str] = None
    bounding_box: Optional[Dict[str, Any]] = None
    extraction_status: ExtractionStatusEnum
    created_at: Optional[datetime] = None


class DeclarationUpdatePayload(BaseModel):
    normalized_value: Optional[str] = Field(
        default=None, description="Corrected or verified declaration value"
    )
    extraction_status: Optional[ExtractionStatusEnum] = Field(
        default=None, description="Updated status e.g. DETECTED, UNVERIFIED"
    )
    notes: Optional[str] = Field(
        default=None, description="Officer notes explaining manual edit"
    )


class ScanDeclarationsResponse(BaseModel):
    scan_id: str
    status: str
    total_declarations: int
    mean_confidence: float
    declarations: List[DeclarationItemSchema]
    disclaimer: str = (
        "Declaration extraction is an automated evidence extraction process. "
        "It identifies packaged commodity declarations and does not constitute a legal compliance determination."
    )
