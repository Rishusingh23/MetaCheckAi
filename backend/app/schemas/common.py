from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field, ConfigDict

T = TypeVar("T")


class PaginationParams(BaseModel):
    skip: int = Field(default=0, ge=0, description="Records to skip")
    limit: int = Field(default=20, ge=1, le=100, description="Records per page (max 100)")


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int = Field(description="Total record count")
    skip: int = Field(description="Skipped count")
    limit: int = Field(description="Page limit size")
    has_more: bool = Field(description="Whether additional records exist")


class MessageResponse(BaseModel):
    success: bool = True
    message: str
