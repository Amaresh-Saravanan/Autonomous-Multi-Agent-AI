"""Typed auth contracts (Phase 5)."""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    agency_id: str
    agency_name: str | None = None
    email: str | None = None
    must_change_password: bool = False


class MeResponse(BaseModel):
    email: str
    role: str
    agency_id: str
    agency_name: str | None = None
    must_change_password: bool = False


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=10, max_length=128)
