"""What the platform console reads and sends about one person's station progress."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class StationProgressRead(BaseModel):
    """One station this person has sat, or holds in a practice set.

    `attempts` counts the attempts that exist; `entry_attempts` is the sum of
    the counters on their set entries, which is what the per-station limit is
    enforced on and what "reset attempts" zeroes. The two agree until somebody
    resets, and showing both is how the console explains the difference.
    """

    station_id: uuid.UUID
    title: str
    exam_code: str
    attempts: int
    evaluated: int
    last_attempt_at: datetime | None
    last_attempt_id: uuid.UUID | None
    last_status: str | None
    entry_attempts: int
    set_entry_ids: list[uuid.UUID] = Field(default_factory=list)


class DeleteStationProgress(BaseModel):
    reason: str = Field(min_length=1, max_length=180)


class StationProgressChange(BaseModel):
    """What one of the two actions did, in numbers the toast can print."""

    station_id: uuid.UUID
    attempts_deleted: int = 0
    entries_reset: int = 0
    entries_removed: int = 0
