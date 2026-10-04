from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.models.report import ReportTypeEnum, ReportFormatEnum, ReportStatusEnum


class ReportBase(BaseModel):
    report_type: ReportTypeEnum = Field(default=ReportTypeEnum.INSPECTION_SUMMARY)
    file_path: Optional[str] = Field(default=None)
    format: ReportFormatEnum = Field(default=ReportFormatEnum.PDF)
    status: ReportStatusEnum = Field(default=ReportStatusEnum.READY)


class ReportCreate(ReportBase):
    inspection_id: str
    generated_by: Optional[str] = None


class ReportRead(ReportBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    inspection_id: str
    generated_by: Optional[str] = None
    generated_at: datetime
    created_at: datetime
