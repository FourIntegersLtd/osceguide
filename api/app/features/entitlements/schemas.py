from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


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
