from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class InspectionHistoryBase(BaseModel):
    action: str = Field(description="Action executed, e.g. STATUS_CHANGED, OFFICER_VERIFIED")
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    change_metadata: Optional[dict] = None


class InspectionHistoryCreate(InspectionHistoryBase):
    inspection_id: str
    user_id: Optional[str] = None


class InspectionHistoryRead(InspectionHistoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    inspection_id: str
    user_id: Optional[str] = None
    timestamp: datetime
