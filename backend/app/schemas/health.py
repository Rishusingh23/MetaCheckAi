from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel, Field, ConfigDict


class HealthResponse(BaseModel):
    """
    Standard Health Check Response Model.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "project_name": "MetaCheck AI",
                "version": "1.0.0",
                "environment": "development",
                "timestamp": "2026-09-14T22:30:00Z",
                "database_connected": True,
                "services": {
                    "api": "healthy",
                    "database": "connected"
                }
            }
        }
    )

    status: str = Field(default="healthy", description="Application health status")
    project_name: str = Field(description="Name of the service")
    version: str = Field(description="Application version")
    environment: str = Field(description="Current deployment environment")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC Timestamp of the check")
    database_connected: bool = Field(default=False, description="Whether PostgreSQL is connected")
    services: Optional[Dict[str, str]] = Field(default=None, description="Component status mapping")

