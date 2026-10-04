from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.schemas.role import RoleRead


class UserBase(BaseModel):
    name: str = Field(min_length=1, max_length=255, description="Full name of user/officer")
    email: EmailStr = Field(description="Official email address")
    role_id: str = Field(description="Role ID reference")
    is_active: bool = Field(default=True, description="Account active status")


class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=100, description="Raw initial password")


class UserUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    role_id: Optional[str] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)
    password: Optional[str] = Field(default=None, min_length=6)


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
    role: Optional[RoleRead] = None
