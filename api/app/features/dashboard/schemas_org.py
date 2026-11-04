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
    """What the setup checklist counts."""

    trainees: int
    stations: int
    # What the platform's library offers for the exams this org runs. `stations`
    # alone said "you have nothing to examine anybody with" to an institution
    # that had adopted the catalogue whole — see `OrgSetup.stations_available`.
    library_stations: int
    staff: int
    programmes_with_markable_exam: int
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

    # The build order, one flag per step. Marking scheme, exam and template are
    # done when the organisation owns a published one or the platform publishes
    # one it may use, the same reading as `stations_available`.
    rubric_published: bool
    exam_published: bool
    template_published: bool
    sitting_scheduled: bool
    trainees_added: bool
    # "There is something to run", not "you have written it yourself". An
    # institution that adopted the platform catalogue can examine somebody
    # today, and telling it otherwise sent it off to author stations it did not
    # need. `OrgCounts.stations` still carries its own authoring separately.
    stations_available: bool
    # Staff beyond the admin who created the organisation: a supervisor or a second admin.
    team_invited: bool
    programme_exam_rubric_ready: bool
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
    # The live attempt, if the patient has been dispatched for this slot.
    attempt_id: uuid.UUID | None = None
    # The circuit's clock, shown against the slot it is on and null elsewhere.
    phase: str | None = None
    phase_started_at: datetime | None = None
    phase_ends_at: datetime | None = None


class ConsoleBreakLength(BaseModel):
    after_station: int
    minutes: int


class ConsoleTiming(BaseModel):
    reading_minutes: int
    simulation_minutes: int
    break_minutes: int
    breaks: list[int] = Field(default_factory=list)
    break_lengths: list[ConsoleBreakLength] = Field(default_factory=list)


class ConsoleCircuit(BaseModel):
    id: uuid.UUID
    name: str
    timing: ConsoleTiming
    active_slot_id: uuid.UUID | None
    room_name: str | None
    started_at: datetime | None
    ended_at: datetime | None
    agent_dispatched: bool
    # What a rebuild names as the revision it read (B-15).
    revision: int = 1
    supervisor: ConsolePerson | None
    # The examination clock, and whether the circuit is still driving itself.
    phase: str | None = None
    phase_started_at: datetime | None = None
    phase_ends_at: datetime | None = None
    # Every transition and every override bumps this. A console that has been
    # open through an override can tell that what it is showing is behind.
    phase_seq: int = 0
    paused: bool = False
    paused_at: datetime | None = None
    auto_advance: bool = True
    # Computed here against the server's clock, so a browser with a wrong
    # system time still shows the right numbers.
    elapsed_seconds: int | None = None
    remaining_seconds: int | None = None
    alerts: list[str] = Field(default_factory=list)
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
    rubric_version_id: uuid.UUID


class CircuitConsole(BaseModel):
    """One request for the screen a supervisor runs an examination from."""

    sitting: ConsoleSitting
    circuit: ConsoleCircuit
    slots: list[ConsoleSlot] = Field(default_factory=list)


class CohortCandidate(BaseModel):
    """One candidate's standing in a sitting."""

    trainee: ConsolePerson
    rank: int
    stations_total: int
    stations_completed: int
    completion_rate: float
    # Null when nothing of theirs has been marked. Deliberately not zero: a
    # zero would rank an unassessed candidate below a failing one.
    assessment_score: float | None
    # Stations whose effective ratings meet the rubric's pass rule; a station
    # with no pass rule or no rating counts as neither passed nor failed.
    stations_passed: int = 0
    # Which candidates a GP lead should look at first: urgent, high, standard
    # or low. An unfinished examination outranks a poor score.
    review_priority: str


class CohortSummary(BaseModel):
    """How a sitting's candidates compare, ranked.

    Exam sittings only. A training circuit is people practising, and ranking
    them against each other would turn practice into an assessment nobody
    agreed to sit.
    """

    sitting_id: uuid.UUID
    sitting_name: str
    cohort_size: int
    candidates: list[CohortCandidate] = Field(default_factory=list)
