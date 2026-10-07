"""The shapes entitlement routes send and receive: grants, and requests to give, extend or revoke one."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.core.pagination import Page

# What a practice-access row says about the person: invited (the account is waiting for them
# to choose a password), active, or revoked (no longer grants anything).
PracticeAccessStatus = Literal["invited", "active", "revoked"]

# What happened to one row of a bulk grant.
PracticeAccessOutcome = Literal["granted", "invited", "already_active", "invalid_email", "unknown_exam"]


class PracticeAccessRead(BaseModel):
    """One person's practice access to one exam, granted by this organisation.

    `access_id` is the entitlement's id. `user_id` is always set today, because an invitation
    creates the account up front; it is nullable in the contract so a pending invitation that
    holds no account could be listed without a breaking change.
    """

    access_id: uuid.UUID
    email: str
    user_id: uuid.UUID | None
    exam_id: uuid.UUID
    exam_code: str
    exam_title: str
    status: PracticeAccessStatus
    granted_at: datetime
    revoked_at: datetime | None


class PracticeAccessList(BaseModel):
    """Everything this organisation has granted as practice access, revoked rows included."""

    items: list[PracticeAccessRead]


class PracticeAccessItem(BaseModel):
    """One practice-access row, wrapped the way the frontend reads a single item."""

    item: PracticeAccessRead


class GrantPracticeAccess(BaseModel):
    """Give one person, who need not have an account yet, practice access to one exam."""

    email: str = Field(min_length=1, max_length=320)
    exam_id: uuid.UUID


class PracticeAccessRow(BaseModel):
    """One row of a bulk grant, as the client parsed it from a CSV.

    `exam_id` is a string rather than a uuid so one malformed cell becomes that row's
    `unknown_exam` outcome instead of refusing the whole file.
    """

    email: str = Field(max_length=320)
    exam_id: str = Field(max_length=64)


class BulkGrantPracticeAccess(BaseModel):
    """Up to 500 rows granted in one request."""

    rows: list[PracticeAccessRow] = Field(min_length=1, max_length=500)


class PracticeAccessResult(BaseModel):
    """What happened to one row of a bulk grant."""

    email: str
    outcome: PracticeAccessOutcome


class BulkPracticeAccessResults(BaseModel):
    """One result per row, in the order the rows were sent."""

    results: list[PracticeAccessResult]


class EntitlementRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    exam_id: uuid.UUID
    exam_code: str
    source: str
    starts_at: datetime
    ends_at: datetime | None
    revoked_at: datetime | None
    live: bool


class TrialLimits(BaseModel):
    """What the free trial allows, so a screen never hard-codes it."""

    stations: int
    days: int
    attempts_per_station: int


class MyEntitlements(Page[EntitlementRead]):
    """A person's grants, with the limits of the free trial they fall back on."""

    trial: TrialLimits


class GrantEntitlement(BaseModel):
    """An institution granting one of its people access to an exam it runs.

    By email, as everything an administrator does is. `ends_at` left empty is
    open-ended; an institution usually sets it to the end of the academic year.
    """

    email: str
    exam_code: str
    ends_at: datetime | None = None


class PlatformEntitlementRead(EntitlementRead):
    """A grant as the platform console reads it: where it came from, who made it."""

    source_ref: str | None
    org_id: uuid.UUID | None
    granted_by: uuid.UUID | None


class PlatformGrantEntitlement(BaseModel):
    """A platform admin granting access outright — a refund made good, a
    sponsor's seat, a support gesture. `note` is why, and goes in the audit row."""

    exam_code: str = Field(min_length=1, max_length=32)
    ends_at: datetime | None = None
    note: str = Field(min_length=1, max_length=500)


class ExtendEntitlement(BaseModel):
    """Move the end date. `None` makes the grant open-ended."""

    ends_at: datetime | None = None
    note: str | None = Field(default=None, max_length=500)


class RevokeEntitlement(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
