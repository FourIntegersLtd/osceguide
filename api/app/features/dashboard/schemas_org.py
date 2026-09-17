"""The shapes the institutional screens need, assembled server-side.

Read models, like `schemas.py`: nothing here is owned by anybody. The console
is the one that matters most — the supervisor's screen polls circuit state
every eight seconds and resolves each station title and each candidate name
one request at a time, and every one of those fields is in `CircuitConsole`.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class OrgCounts(BaseModel):
    """What the setup checklist counts. Four legacy calls existed to produce these."""

    trainees: int
    stations: int
    staff: int
    published_feedback_templates: int
    sittings: int


class OrgSittingRow(BaseModel):
    id: uuid.UUID
    name: str
    mode: str
    status: str
    scheduled_for: datetime | None


class OrgSetup(BaseModel):
    """Whether the organisation can actually hold a sitting yet.

    Each flag is a step the browser was deriving from a list it fetched only to
    take the length of.
    """

    trainees_added: bool
    stations_authored: bool
    team_invited: bool
    feedback_template_published: bool
    ready_to_run: bool


class OrgDashboard(BaseModel):
    org_id: uuid.UUID
    slug: str
    name: str
    counts: OrgCounts
    setup: OrgSetup
    recent_sittings: list[OrgSittingRow] = Field(default_factory=list)


class SupervisorCircuitRow(BaseModel):
    """One circuit this person is named on, with the sitting it belongs to."""

    circuit_id: uuid.UUID
    circuit_name: str
    sitting_id: uuid.UUID
    sitting_name: str
    mode: str
    status: str
    scheduled_for: datetime | None
    slot_count: int
    in_progress: bool
    ended: bool


class SupervisorCircuits(BaseModel):
    items: list[SupervisorCircuitRow] = Field(default_factory=list)


class ConsolePerson(BaseModel):
    user_id: uuid.UUID
    name: str | None = None
    email: str | None = None
    # Null when this person is not on the organisation's roster: a slot names a
    # user, and rostering is a separate act.
    trainee_id: uuid.UUID | None = None


class ConsoleStation(BaseModel):
    """Null fields mean the version is not readable by this org, not that it is untitled."""

    version_id: uuid.UUID
    station_id: uuid.UUID | None = None
    title: str | None = None
    version: int | None = None
    status: str | None = None


class ConsoleSlot(BaseModel):
    id: uuid.UUID
    slot_index: int
    status: str
    room_name: str | None
    started_at: datetime | None
    ended_at: datetime | None
    exam_completed_at: datetime | None
    trainee: ConsolePerson
    station: ConsoleStation
    # Whether this slot has been marked. The console probed one request per
    # slot for this.
    has_review: bool
    is_active: bool


class ConsoleTiming(BaseModel):
    reading_minutes: int
    simulation_minutes: int
    breaks: list[int] = Field(default_factory=list)


class ConsoleCircuit(BaseModel):
    id: uuid.UUID
    name: str
    timing: ConsoleTiming
    active_slot_id: uuid.UUID | None
    room_name: str | None
    started_at: datetime | None
    ended_at: datetime | None
    agent_dispatched: bool
    supervisor: ConsolePerson | None
    # From the same rule the edit-lock route serves, so the console does not
    # have to ask twice.
    editable: bool
    edit_block: str | None


class ConsoleSitting(BaseModel):
    id: uuid.UUID
    name: str
    mode: str
    sitting_type: str
    status: str
    scheduled_for: datetime | None
    feedback_template_version_id: uuid.UUID


class CircuitConsole(BaseModel):
    """One request for the screen a supervisor runs an examination from."""

    sitting: ConsoleSitting
    circuit: ConsoleCircuit
    slots: list[ConsoleSlot] = Field(default_factory=list)
