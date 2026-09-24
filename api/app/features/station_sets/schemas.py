from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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


class UpdateSet(BaseModel):
    """What a learner may still change about a set they have built.

    The name, and only the name. A set carries no description and no timings —
    the length of a session is the sum of its stations' exam timings, which the
    exam owns — so there is nothing else to write, and the retiring client's
    edit screen asked for a name and a list of stations and nothing more.

    Whitespace strips to nothing, which is then too short: a set called `"   "`
    is an unlabelled row in the list the learner has to keep.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)


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
