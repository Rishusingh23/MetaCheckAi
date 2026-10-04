from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    """Payload for officer/user login authentication."""
    email: EmailStr = Field(..., description="Officer or administrative email address")
    password: str = Field(..., min_length=1, description="Account password")


class UserAuthRead(BaseModel):
    """Current authenticated user profile summary."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: EmailStr
    role: str
    is_active: bool


class TokenResponse(BaseModel):
    """JWT access token response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserAuthRead


class LogoutResponse(BaseModel):
    """Response model for token logout / revocation."""
    message: str
    success: bool = True
