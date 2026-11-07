"""The request and response shapes this slice's routes speak in.

Plain data, not domain rules: what a client sends to build or edit a circuit,
and what it reads back about a sitting, a circuit or a slot.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.core.schemas import AudienceSectionRead


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


class BreakLength(BaseModel):
    """A break whose length differs from the circuit's default, named by the station it follows."""

    after_station: int
    minutes: int


class TimingRead(BaseModel):
    reading_minutes: int
    simulation_minutes: int
    break_minutes: int
    # Which stations a break follows, 1-based, as an examiner writes it.
    breaks: list[int] = Field(default_factory=list)
    break_lengths: list[BreakLength] = Field(default_factory=list)


class CircuitRead(BaseModel):
    id: uuid.UUID
    revision: int = 1
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
    # Training rooms: everyone may speak, and when the supervisor closed the room kept open after End.
    open_floor: bool = False
    room_closed_at: datetime | None = None
    # Distinct trainees on this circuit (derived from its slots).
    trainee_count: int = 0
    # The supervisor's display name; filled where a screen lists circuits.
    supervisor_name: str | None = None
    slots: list[SlotRead] = Field(default_factory=list)


class SittingRead(BaseModel):
    id: uuid.UUID
    revision: int = 1
    name: str
    mode: str
    sitting_type: str
    status: str
    scheduled_for: datetime | None
    rubric_version_id: uuid.UUID
    programme_id: uuid.UUID | None = None
    # The intake the sitting is held for, if any.
    cohort_id: uuid.UUID | None = None
    # The exam name the programme offers, and distinct candidates across the
    # sitting's circuits. Filled by the list and detail reads.
    programme_name: str | None = None
    # The code of that exam, which is what the station library is filtered by.
    exam_code: str | None = None
    candidate_count: int = 0
    # How many circuits the sitting has; none means its circuits are still to be built.
    circuit_count: int = 0
    circuits: list[CircuitRead] = Field(default_factory=list)


class CreateSitting(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    programme_id: uuid.UUID
    mode: str = Field(default="training", pattern="^(training|exam)$")
    sitting_type: str = Field(default="group_training", max_length=32)
    scheduled_for: datetime | None = None
    cohort_id: uuid.UUID | None = None


class UpdateSitting(BaseModel):
    """Fields to change on a sitting. An omitted field is left alone.

    `status` is not offered here: that belongs to the run machine, not this
    route.
    """

    name: str | None = Field(default=None, min_length=1, max_length=200)
    mode: str | None = Field(default=None, pattern="^(training|exam)$")
    sitting_type: str | None = Field(default=None, max_length=32)
    scheduled_for: datetime | None = None
    programme_id: uuid.UUID | None = None
    # A null clears the cohort; leave it out to keep it.
    cohort_id: uuid.UUID | None = None
    # The revision the caller read; an older one is refused 409 `stale_revision` (B-15).
    revision: int | None = None


class TimingIn(BaseModel):
    reading_minutes: int | None = None
    simulation_minutes: int | None = None
    break_minutes: int | None = None
    breaks: list[int] = Field(default_factory=list)
    break_lengths: list[BreakLength] = Field(default_factory=list)


class CreateCircuit(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    trainee_ids: list[uuid.UUID]
    station_version_ids: list[uuid.UUID]
    supervisor_user_id: uuid.UUID | None = None
    timing: TimingIn = Field(default_factory=TimingIn)


class CreateExamCircuits(BaseModel):
    """One exam circuit per candidate, all with the same stations, lead and timing."""

    name_prefix: str = Field("Exam", min_length=1, max_length=120)
    candidate_user_ids: list[uuid.UUID] = Field(min_length=1, max_length=200)
    station_version_ids: list[uuid.UUID]
    supervisor_user_id: uuid.UUID | None = None
    timing: TimingIn | None = None

    @field_validator("candidate_user_ids")
    @classmethod
    def _no_repeats(cls, ids: list[uuid.UUID]) -> list[uuid.UUID]:
        """Refuse a candidate listed twice, so nobody gets two circuits by accident."""
        if len(set(ids)) != len(ids):
            raise ValueError("a candidate can be listed only once")
        return ids


class RebuildCircuit(BaseModel):
    """A circuit's full new roster and stations.

    Both lists are sent whole, not as a patch: the slots are rebuilt from
    them. `name`, `supervisor_user_id` and `timing` are left as they are when
    omitted.
    """

    trainee_ids: list[uuid.UUID]
    station_version_ids: list[uuid.UUID]
    name: str | None = Field(default=None, min_length=1, max_length=200)
    supervisor_user_id: uuid.UUID | None = None
    timing: TimingIn | None = None
    # The revision the caller read; an older one is refused 409 `stale_revision` (B-15).
    revision: int | None = None


class Override(BaseModel):
    """Why the override was done. Optional free text, recorded beside the
    action for later review."""

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
    """Who has just arrived, and where they go.

    `station_version_ids` pairs positionally with `trainee_ids` — the nth
    arrival takes the nth station. Omit it and everyone joins the station the
    circuit is currently running.
    """

    trainee_ids: list[uuid.UUID] = Field(min_length=1)
    station_version_ids: list[uuid.UUID] = Field(default_factory=list)


class RoomGrant(BaseModel):
    """What a browser needs to join a circuit's room, and nothing more.

    A candidate taking their place before their station starts, or an examiner
    stepping in to watch. Neither names a recording: the candidate has none
    yet and the examiner never will.
    """

    token: str
    server_url: str
    room: str
    # A candidate's grant is always `True`, so this field is only interesting
    # on the observer grant, where it now varies with the sitting's mode. The
    # browser needs to know before it offers a camera button, not discover it
    # from a publish failure the token silently enforces.
    can_publish: bool = True


class FloorChange(BaseModel):
    open: bool


class MicChange(BaseModel):
    allowed: bool


class SchemeRead(BaseModel):
    """The marking scheme of the station running now, in the author's form, and nothing else.

    No system prompt, pacing or notes: this is what the people watching a training station read.
    """

    slot_id: uuid.UUID
    structure: dict[str, Any]


class SlotBriefRead(BaseModel):
    """A candidate's reading brief for one of their slots, during reading time and after."""

    slot_id: uuid.UUID
    station_title: str
    # The station template's candidate sections, in template order.
    sections: list[AudienceSectionRead] = []
    # A station bound to no template carries its brief as one text instead.
    text: str | None = None


class PeerMarkIn(BaseModel):
    """One mark or comment on one scheme item (`domainId` or `domainId.competencyId`)."""

    item: str = Field(min_length=1, max_length=160)
    rating: str | None = Field(default=None, max_length=16)
    comment: str | None = Field(default=None, max_length=2000)


class SavePeerMarks(BaseModel):
    marks: list[PeerMarkIn] = Field(max_length=200)


class PeerMarkRead(BaseModel):
    marker_id: uuid.UUID
    marker_name: str
    item: str
    rating: str | None = None
    comment: str | None = None


class PeerMarksRead(BaseModel):
    slot_id: uuid.UUID
    items: list[PeerMarkRead]
