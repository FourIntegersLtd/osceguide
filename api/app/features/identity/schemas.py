"""The public shape of identity. Declared here, mapped in the service."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class MembershipRead(BaseModel):
    org_id: uuid.UUID
    org_slug: str
    # Optional because the lookup that fills it is a display concern: a
    # membership authorises with its slug and role alone.
    org_name: str | None = None
    # What the organisation is for: "institution" or "partner". The frontend
    # chooses which workspace shell to render from this, so a partner sees
    # their funnel where an institution sees its cohort.
    org_type: str | None = None
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
    # When they sit the real thing, and what extra reading time they are
    # granted. Both are the person's own, and both are on `/me` because every
    # screen that needs them already reads it.
    exam_date: date | None = None
    extra_reading_percent: int = 0
    # Which exam this account is for, chosen at sign-up. A preference, not a
    # grant: what somebody may open is decided by their entitlements, and this
    # is not resolved against the catalogue here because `identity` sits below
    # it. `GET /me/dashboard` is what turns it into an exam somebody can use.
    exam_code: str | None = None


class UpdateMe(BaseModel):
    """What a person may change about themselves. Absent means "leave it"."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    exam_date: date | None = None
    extra_reading_percent: int | None = Field(default=None, ge=0, le=100)
    exam_code: str | None = Field(default=None, min_length=1, max_length=32)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 - a scheme name, not a secret
    expires_in: int


class AuthResult(TokenPair):
    user: UserRead


class StreamTicket(BaseModel):
    """A short-lived credential for one `EventSource` connection.

    `EventSource` cannot send an `Authorization` header; see `core.streams` for
    why this exists rather than a cookie or a token in the query string.
    """

    ticket: str
    expires_in: int


class RegisterRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1, max_length=512)
    # Which exam they came to sit. The per-exam landing pages carry it into the
    # form, which is how the retiring client's per-exam subdomains are replaced
    # on one domain. Optional, because an institution's member registers
    # without one and gets their exams from the organisation.
    exam_code: str | None = Field(default=None, min_length=1, max_length=32)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=512)


class LegacyExchangeRequest(BaseModel):
    """Trade a token one of the legacy backends issued for a platform pair.

    `provider` is a closed set rather than a string because it selects the
    secret the token is verified against; an open one would let the caller
    choose its own key.
    """

    provider: Literal["consumer", "institution"]
    token: str = Field(min_length=1, max_length=4096)


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    """The session to end.

    Optional: without it every session ends, which is what "sign me out
    everywhere" means. With it only the presented chain goes, so signing out on
    a phone leaves the laptop signed in.
    """

    refresh_token: str | None = None


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
