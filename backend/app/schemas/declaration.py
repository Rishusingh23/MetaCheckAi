from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.models.declaration import DeclarationTypeEnum, ExtractionStatusEnum


class DeclarationBase(BaseModel):
    declaration_type: DeclarationTypeEnum = Field(description="Statutory declaration category")
    raw_value: str = Field(description="Extracted value literal")
    normalized_value: Optional[str] = Field(default=None, description="Cleaned/standardized representation")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    source_text: Optional[str] = Field(default=None, description="Surrounding contextual sentence")
    bounding_box: Optional[dict] = Field(default=None, description="Coordinates on package panel")
    extraction_status: ExtractionStatusEnum = Field(default=ExtractionStatusEnum.DETECTED)


class DeclarationCreate(DeclarationBase):
    scan_id: str


class DeclarationRead(DeclarationBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    scan_id: str
    created_at: datetime
