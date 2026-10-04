from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class OCRResultBase(BaseModel):
    extracted_text: str = Field(description="Raw text detected in image")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    bounding_boxes: Optional[dict] = Field(default=None, description="Spatial coordinates of detected text tokens")
    ocr_engine: Optional[str] = Field(default=None, description="OCR engine identifier")
    processing_metadata: Optional[dict] = Field(default=None)


class OCRResultCreate(OCRResultBase):
    scan_id: str


class OCRResultRead(OCRResultBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    scan_id: str
    created_at: datetime
