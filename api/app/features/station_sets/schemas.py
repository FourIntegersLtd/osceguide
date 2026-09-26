"""The shapes station set routes send and receive: sets, entries and a candidate's progress."""

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
    # The status of the most recently created attempt against this entry, or
    # `None` if it has never been attempted. `feedback_ready` is derived from
    # this rather than duplicating the same check on the client: a station
    # last sat is not the same as a station last marked, and re-attempting a
    # station whose earlier sit was evaluated must not keep showing "Feedback"
    # for a consultation still in progress.
    last_attempt_status: str | None = None
    feedback_ready: bool = False


class SetRead(BaseModel):
    id: uuid.UUID
    name: str
    exam_code: str
    locked: bool
    completed_at: datetime | None
    attempted_entries: int
    total_entries: int
    entries: list[EntryRead] = Field(default_factory=list)
    # True once any one entry's latest attempt has been marked, so the session
    # list can show legacy's "Feedback" badge and a "Review" action instead of
    # "Start" without the client re-deriving it from every entry.
    feedback_ready: bool = False


class CreateSet(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    exam_code: str = Field(min_length=1, max_length=32)
    station_version_ids: list[uuid.UUID] = Field(min_length=1)


class UpdateSet(BaseModel):
    """What a learner may still change about a set they have built.

    The name, and — since this replaces the legacy "edit session" screen — the
    stations themselves. Swapping the list does not touch an entry that stays
    in it: its counters are what an attempt points at, so `replace_entries`
    matches kept versions back onto their existing entry rather than deleting
    and recreating it. A set carries no description and no timings — the
    length of a session is the sum of its stations' exam timings, which the
    exam owns — so there is nothing else to write.

    Whitespace strips to nothing, which is then too short: a set called `"   "`
    is an unlabelled row in the list the learner has to keep.

    `station_version_ids` left out (`None`) means "just the name"; an empty
    list is a real request to empty the set, and is rejected only if that
    would mean removing a station that already has an attempt against it.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    station_version_ids: list[uuid.UUID] | None = None


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


# --- What the platform console reads and sends about one person's station progress.


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
