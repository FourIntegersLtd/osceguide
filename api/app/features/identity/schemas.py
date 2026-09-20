"""The public shape of identity. Declared here, mapped in the service."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class MembershipRead(BaseModel):
    org_id: uuid.UUID
    org_slug: str
    org_name: str
    role: str
    surface: str | None = None


class FlagStationBody(BaseModel):
    station_id: uuid.UUID


class UserRead(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    is_platform_admin: bool
    must_change_password: bool
    memberships: list[MembershipRead] = Field(default_factory=list)
    active_org_slug: str | None = None
    last_login_at: datetime | None = None


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 - a scheme name, not a secret
    expires_in: int


class AuthResult(TokenPair):
    user: UserRead


class RegisterRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1, max_length=512)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=512)


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    password: str = Field(min_length=1, max_length=512)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=512)
    new_password: str = Field(min_length=1, max_length=512)


class Accepted(BaseModel):
    """Returned where the answer must not depend on whether a record exists."""

    status: str = "accepted"
