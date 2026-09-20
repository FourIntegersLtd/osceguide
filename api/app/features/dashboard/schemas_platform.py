"""The account directory: what the platform console lists about everybody.

A read model over five slices — the account, its payments, its attempts, its
grants and the exam catalogue — which is why it lives here rather than on
`GET /platform/users`, whose slice sits below four of them.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DirectoryUser(BaseModel):
    """One row of the directory: the seven columns the retiring console had,
    each answered by the slice that owns the fact."""

    id: uuid.UUID
    email: str
    name: str
    created_at: datetime
    status: str
    is_platform_admin: bool
    exam_code: str | None
    last_login_at: datetime | None
    # A refresh chain neither expired nor revoked — the old "Online" column.
    signed_in: bool
    # Any payment at all. The old `has_paid`.
    has_paid: bool
    # What the most recent payment bought, and when it was made.
    plan_code: str | None
    last_paid_at: datetime | None
    # The furthest end of any live grant, or None for open-ended or nothing.
    access_ends_at: datetime | None
    live_exam_codes: list[str] = Field(default_factory=list)
    attempt_count: int


class ExamDirectorySummary(BaseModel):
    """How many accounts an exam has, split the way the old filter did."""

    code: str
    name: str
    users: int
    paid: int
    trial: int
    not_started: int


class DirectorySummary(BaseModel):
    exams: list[ExamDirectorySummary]
    # Accounts naming no exam and holding no live grant.
    unassigned: int
    total: int
