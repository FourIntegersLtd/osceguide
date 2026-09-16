from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class EntitlementRead(BaseModel):
    id: uuid.UUID
    exam_id: uuid.UUID
    exam_code: str
    source: str
    starts_at: datetime
    ends_at: datetime | None
    revoked_at: datetime | None
    live: bool


class GrantEntitlement(BaseModel):
    email: str
    exam_code: str
    ends_at: datetime | None = None
