from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.models.user import RoleEnum


class RoleBase(BaseModel):
    name: RoleEnum = Field(description="Role identifier enum")
    description: Optional[str] = Field(default=None, description="Role description")


class RoleCreate(RoleBase):
    pass


class RoleRead(RoleBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
