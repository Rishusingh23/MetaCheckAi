from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.models.scan import ScanStatusEnum, PanelTypeEnum


class ScanBase(BaseModel):
    image_path: str = Field(description="Path to processed label image")
    panel_type: PanelTypeEnum = Field(default=PanelTypeEnum.FRONT_PDP)
    processing_status: ScanStatusEnum = Field(default=ScanStatusEnum.PENDING)


class ScanCreate(ScanBase):
    inspection_id: str
    product_image_id: Optional[str] = None


class ScanUpdate(BaseModel):
    processing_status: Optional[ScanStatusEnum] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class ScanRead(ScanBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    inspection_id: str
    product_image_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
