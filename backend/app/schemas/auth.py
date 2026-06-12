"""Pydantic schemas for authentication endpoints."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, field_validator


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    phone: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("নাম খালি রাখা যাবে না")
        return v

    @field_validator("email")
    @classmethod
    def email_normalise(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def password_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("পাসওয়ার্ড কমপক্ষে ৬ অক্ষরের হতে হবে")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def email_normalise(cls, v: str) -> str:
        return v.strip().lower()


class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str]
    phone: Optional[str] = None
    role: str
    plan: str
    query_count_today: int
    query_limit: int
    is_admin: bool = False
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("নাম খালি রাখা যাবে না")
        return v


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def new_password_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("পাসওয়ার্ড কমপক্ষে ৬ অক্ষরের হতে হবে")
        return v
