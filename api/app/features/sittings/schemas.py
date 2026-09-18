from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SlotRead(BaseModel):
    id: uuid.UUID
    slot_index: int
    trainee_id: uuid.UUID
    station_version_id: uuid.UUID
    status: str
    room_name: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    # The circuit's clock, shown against the slot it is currently on and null
    # for every other slot. Derived, not stored: the clock is the circuit's.
    phase: str | None = None
    phase_started_at: datetime | None = None
    phase_ends_at: datetime | None = None


class TimingRead(BaseModel):
    reading_minutes: int
    simulation_minutes: int
    break_minutes: int
    # Which stations a break follows, 1-based, as an examiner writes it.
    breaks: list[int] = Field(default_factory=list)


class CircuitRead(BaseModel):
    id: uuid.UUID
    sitting_id: uuid.UUID
    name: str
    supervisor_user_id: uuid.UUID | None
    timing: TimingRead
    active_slot_id: uuid.UUID | None
    room_name: str | None
    started_at: datetime | None
    ended_at: datetime | None
    # The examination clock (D-6). One deadline, read by every screen.
    phase: str | None = None
    phase_started_at: datetime | None = None
    phase_ends_at: datetime | None = None
    # Bumped by every transition and override. A client that acts on a stale
    # screen can be told so, and a scheduled transition that no longer matches
    # does nothing.
    phase_seq: int = 0
    paused: bool = False
    paused_at: datetime | None = None
    auto_advance: bool = True
    slots: list[SlotRead] = Field(default_factory=list)


class SittingRead(BaseModel):
    id: uuid.UUID
    name: str
    mode: str
    sitting_type: str
    status: str
    scheduled_for: datetime | None
    feedback_template_version_id: uuid.UUID
    circuits: list[CircuitRead] = Field(default_factory=list)


class CreateSitting(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    feedback_template_version_id: uuid.UUID
    mode: str = Field(default="training", pattern="^(training|exam)$")
    sitting_type: str = Field(default="group_training", max_length=32)
    scheduled_for: datetime | None = None
    programme_id: uuid.UUID | None = None


class TimingIn(BaseModel):
    reading_minutes: int | None = None
    simulation_minutes: int | None = None
    break_minutes: int | None = None
    breaks: list[int] = Field(default_factory=list)


class CreateCircuit(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    trainee_ids: list[uuid.UUID]
    station_version_ids: list[uuid.UUID]
    supervisor_user_id: uuid.UUID | None = None
    timing: TimingIn = Field(default_factory=TimingIn)


class RebuildCircuit(BaseModel):
    """A circuit's new shape. Everything omitted is left as it is.

    The trainees and the stations are sent whole rather than as a patch: the
    slots are rebuilt from them, and a partial edit would leave the API
    guessing which pairing the supervisor meant.
    """

    trainee_ids: list[uuid.UUID]
    station_version_ids: list[uuid.UUID]
    name: str | None = Field(default=None, min_length=1, max_length=200)
    supervisor_user_id: uuid.UUID | None = None
    timing: TimingIn | None = None


class Override(BaseModel):
    """What every override may carry: why it was done.

    Optional, and free text, because the reasons are the ones nobody predicted
    — that is what an override is for. It is written to the record beside the
    action, so "the clock was extended" is answerable with "because the fire
    alarm went".
    """

    reason: str | None = Field(default=None, max_length=500)


class ExtendClock(Override):
    # An hour is generous for a station and short enough that a mistyped value
    # cannot strand a circuit until the reaper finds it.
    seconds: int = Field(ge=1, le=3600)


class StationOverride(Override):
    slot_id: uuid.UUID


class SetAutoAdvance(BaseModel):
    enabled: bool


class Intervention(BaseModel):
    id: uuid.UUID
    circuit_id: uuid.UUID
    slot_id: uuid.UUID | None
    actor_user_id: uuid.UUID | None
    action: str
    reason: str | None
    phase_seq_before: int
    phase_seq_after: int
    at: datetime


class Interventions(BaseModel):
    items: list[Intervention] = Field(default_factory=list)


class DispatchResult(BaseModel):
    room_name: str
    slot_id: uuid.UUID
    # The attempt the worker will bootstrap. A re-dispatch is a new attempt,
    # so this changes each time (C6).
    attempt_id: uuid.UUID
    agent_name: str
    stale_agents_removed: int


class EditLock(BaseModel):
    circuit_id: uuid.UUID
    editable: bool
    # A stable code the client switches on, never a sentence.
    reason: str | None


class AppendTrainees(BaseModel):
    trainee_ids: list[uuid.UUID] = Field(min_length=1)


class RoomGrant(BaseModel):
    """What a browser needs to join a circuit's room, and nothing more.

    A candidate taking their place before their station starts, or an examiner
    stepping in to watch. Neither names a recording: the candidate has none yet
    and the examiner never will, which is what separates this from the token
    issued against an attempt.

    This slice's own shape rather than `voice`'s, even though the two agree
    today: a wire contract belongs to the routes that serve it, and sharing one
    is how two slices come to be unable to change it separately.
    """

    token: str
    server_url: str
    room: str
