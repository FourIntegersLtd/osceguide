"""The shape one screen needs, assembled server-side.

A read model, not a domain entity. "Dashboard" names a projection over several
aggregates; nothing owns a dashboard and no rule is enforced about one.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ExamProgress(BaseModel):
    exam_code: str
    attempts: int
    evaluated: int
    last_attempt_at: datetime | None = None


class RecentAttempt(BaseModel):
    id: uuid.UUID
    kind: str
    status: str
    exam_code: str
    created_at: datetime
    has_result: bool


class SetSummary(BaseModel):
    id: uuid.UUID
    name: str
    exam_code: str
    attempted_entries: int
    total_entries: int
    locked: bool


class EntitlementSummary(BaseModel):
    exam_code: str
    source: str
    ends_at: datetime | None
    live: bool


class Dashboard(BaseModel):
    """Replaces seven calls on the SCA dashboard alone.

    The legacy screen fans out to four RAG endpoints, a weekly trend and two
    marketplace lists, then joins them in the browser.
    """

    user_id: uuid.UUID
    entitlements: list[EntitlementSummary] = Field(default_factory=list)
    progress: list[ExamProgress] = Field(default_factory=list)
    recent_attempts: list[RecentAttempt] = Field(default_factory=list)
    sets: list[SetSummary] = Field(default_factory=list)
    # Which exams this person may open, and which one their screens start on.
    # Answered here so no screen has to guess: the retiring client took it from
    # the subdomain, and without it four screens each derived a different
    # answer from a different source and offered a picker over the whole
    # catalogue. `exam_codes` holds only live access plus the exam the account
    # was opened for; see
    # `entitlements.domain_access`.
    exam_codes: list[str] = Field(default_factory=list)
    current_exam_code: str | None = None


class PerformanceSummary(BaseModel):
    """How the marked attempts divide, as rates rather than counts.

    Rates because the chart draws bands, and because a candidate with four
    attempts and one with forty should read the same way.
    """

    pass_rate: float
    fail_rate: float
    critical_rate: float


class DomainScore(BaseModel):
    """One bar of the radar: a rubric domain, averaged across the attempts."""

    id: str
    label: str
    score: float


class TrendPoint(BaseModel):
    """One attempt, in the order it was sat."""

    date: datetime
    score: float


class DomainComposition(BaseModel):
    """How many marked attempts landed red, amber or green on one domain.

    Classed from the same 0–100 domain score the bars already use: 83 and
    above is green (a clear G), 50 to 83 is amber, below that is red. Counts,
    not a new mark.
    """

    id: str
    label: str
    red: int
    amber: int
    green: int


class Performance(BaseModel):
    """The charts on the consumer exam dashboard, in one call.

    The legacy screen asks four RAG endpoints and a weekly trend for this and
    joins them in the browser. `exam_code` is null only when the caller named
    no exam and has never attempted one — there is no exam to report on, and
    an empty string would be a code.
    """

    exam_code: str | None = None
    summary: PerformanceSummary
    domains: list[DomainScore] = Field(default_factory=list)
    trend: list[TrendPoint] = Field(default_factory=list)
    composition: list[DomainComposition] = Field(default_factory=list)


class MySlot(BaseModel):
    """A station this person is rostered onto, from their side of it."""

    id: uuid.UUID
    slot_index: int
    status: str
    room_name: str | None
    station_title: str | None
    # The station and its version, so the frontend can match a slot to a
    # station without title-based string matching.
    station_id: uuid.UUID | None = None
    station_version_id: uuid.UUID | None = None
    started_at: datetime | None
    ended_at: datetime | None
    exam_completed_at: datetime | None
    # Whether the portal should offer to join: a room exists, the circuit is
    # running, and this station is not already finished.
    joinable: bool
    # The attempt the supervisor's dispatch created for this slot, once there
    # is one. The voice token is issued per attempt, so without this a
    # candidate had no way to ask for one.
    attempt_id: uuid.UUID | None = None
    # The circuit's clock, shown against the station it is on and null for the
    # rest. Derived, because the clock belongs to the circuit.
    phase: str | None = None
    phase_started_at: datetime | None = None
    phase_ends_at: datetime | None = None
    # Whether this is the station the circuit is actually on.
    is_active: bool = False


class MySitting(BaseModel):
    id: uuid.UUID
    name: str
    mode: str
    status: str
    scheduled_for: datetime | None
    org_id: uuid.UUID
    org_slug: str | None
    circuit_id: uuid.UUID
    circuit_name: str
    # The circuit's own state, which is what a candidate actually watches: they
    # are in one room for the whole examination, and what changes is the phase.
    live: bool = False
    # Whether to offer the room. A candidate joins once, at the start, and
    # stays — waiting for a per-station button was the browser's idea, not an
    # examination's.
    can_join: bool = False
    phase: str | None = None
    phase_started_at: datetime | None = None
    phase_ends_at: datetime | None = None
    paused: bool = False
    # Counted here against the server's clock, so a candidate with a wrong
    # system time is not told they have four minutes when they have one.
    remaining_seconds: int | None = None
    active_slot_id: uuid.UUID | None = None
    slots: list[MySlot] = Field(default_factory=list)


class MySittings(BaseModel):
    """The trainee portal's whole screen, in one request.

    It polls two lists every five seconds and joins them in the browser to
    answer one question: is it my turn yet?
    """

    items: list[MySitting] = Field(default_factory=list)
