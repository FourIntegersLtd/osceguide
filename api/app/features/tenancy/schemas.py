from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class OrganizationRead(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    org_type: str
    status: str
    created_at: datetime


class CreateOrganization(BaseModel):
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9-]*$")
    name: str = Field(min_length=1, max_length=200)
    org_type: str = Field(default="institution", pattern="^(institution|partner)$")


class MembershipRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str | None = None
    role: str
    product_surface: str | None = None
    status: str
    revoked_at: datetime | None = None


class CreateMembership(BaseModel):
    email: EmailStr
    role: str = Field(min_length=1, max_length=32)
    product_surface: str | None = None


class UpdateMembership(BaseModel):
    role: str = Field(min_length=1, max_length=32)


class SwitchWorkspace(BaseModel):
    org_slug: str


class WorkspaceToken(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 - a scheme name, not a secret
    expires_in: int
    active_org_slug: str
    active_role: str


class AuditRead(BaseModel):
    id: uuid.UUID
    actor_email: str | None
    action: str
    target_type: str | None
    target_id: str | None
    summary: str | None
    at: datetime


class Capabilities(BaseModel):
    """What the caller may do, decided here rather than in the browser.

    The B2B frontend keeps a table mirroring the backend policy and uses it to
    decide whether to issue a request at all. Two copies of an authorisation
    rule is one too many; this is the served answer.
    """

    user_id: uuid.UUID
    is_platform_admin: bool
    active_org_slug: str | None
    active_role: str | None
    can: dict[str, bool]
