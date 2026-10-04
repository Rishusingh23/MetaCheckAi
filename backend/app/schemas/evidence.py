from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.models.evidence import EvidenceSourceTypeEnum


class EvidenceBase(BaseModel):
    source_type: EvidenceSourceTypeEnum = Field(default=EvidenceSourceTypeEnum.LABEL_IMAGE_CROP)
    image_url_or_path: Optional[str] = Field(default=None)
    bounding_box: Optional[dict] = Field(default=None)
    description: Optional[str] = Field(default=None)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class EvidenceCreate(EvidenceBase):
    inspection_id: str
    violation_id: Optional[str] = None


class EvidenceRead(EvidenceBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    inspection_id: str
    violation_id: Optional[str] = None
    created_at: datetime
