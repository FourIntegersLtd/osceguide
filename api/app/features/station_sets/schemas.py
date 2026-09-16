from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class EntryRead(BaseModel):
    id: uuid.UUID
    position: int
    station_version_id: uuid.UUID
    attempts: int
    debrief_attempts: int
    last_attempt_at: datetime | None = None


class SetRead(BaseModel):
    id: uuid.UUID
    name: str
    exam_code: str
    locked: bool
    completed_at: datetime | None
    attempted_entries: int
    total_entries: int
    entries: list[EntryRead] = Field(default_factory=list)


class CreateSet(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    exam_code: str = Field(min_length=1, max_length=32)
    station_version_ids: list[uuid.UUID] = Field(min_length=1)


class StartedAttempt(BaseModel):
    """What starting a set entry returns.

    Deliberately this slice's own shape rather than `attempts`' response model.
    They would look alike today and diverge the moment either contract moves,
    and a client of one should not break because the other added a field.
    """

    attempt_id: uuid.UUID
    kind: str
    status: str
    entry_id: uuid.UUID
    attempts_used: int
