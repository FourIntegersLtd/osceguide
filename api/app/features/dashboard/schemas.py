"""The shape one screen needs, assembled server-side."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.core.exam_settings import ExamSettings
from app.core.schemas import RatingRead


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


class DashboardExam(BaseModel):
    """The exam the screens start on, with the settings that shape them."""

    code: str
    name: str
    settings: ExamSettings


class Dashboard(BaseModel):
    """A trainee's home screen: entitlements, progress, recent attempts and question sets."""

    user_id: uuid.UUID
    entitlements: list[EntitlementSummary] = Field(default_factory=list)
    progress: list[ExamProgress] = Field(default_factory=list)
    recent_attempts: list[RecentAttempt] = Field(default_factory=list)
    sets: list[SetSummary] = Field(default_factory=list)
    # Which exams this person may open, and which one their screens start on.
    # `exam_codes` holds only live access plus the exam the account was opened for; see
    # `entitlements.domain_access`.
    exam_codes: list[str] = Field(default_factory=list)
    current_exam_code: str | None = None
    # The same exam as `current_exam_code`, with its name and `settings`, so the
    # screens can label and shape themselves without branching on its code.
    current_exam: DashboardExam | None = None


class PerformanceSummary(BaseModel):
    """How the marked attempts divide, as rates rather than counts."""

    # Null when the exam's rubric sets no pass line: nothing passes or fails.
    pass_rate: float | None
    fail_rate: float | None
    # Attempts that raised at least one critical concern (a flag, or a rating in the poor tone).
    critical_rate: float


class DomainScore(BaseModel):
    """One bar of the radar: a rubric domain, averaged across the attempts marked on it."""

    id: str
    label: str
    # 0-100: the domain's value as a share of its maximum, averaged. Comparable across versions.
    score: float
    # The domain's value in the display's domain aggregate (e.g. 3.2 of 4, 7.5 of 10), averaged.
    value: float | None = None
    # Every rating given in it, per scale value (best first); empty unless the rating is a scale.
    counts: dict[str, int] = Field(default_factory=dict)


class TrendPoint(BaseModel):
    """One attempt, in the order it was sat."""

    date: datetime
    # 0-100: the station total as a share of its maximum.
    score: float
    # The station total in the rubric's units (e.g. 9 of 12, 38 of 50).
    total: float | None = None
    passed: bool | None = None


class DomainComposition(BaseModel):
    """How many marked attempts landed in each tone on one domain.

    A domain's tone comes from its value as a share of its maximum, read
    against the display's tones. `red`/`amber`/`green` are the poor, fair and
    good-or-better counts, kept until the web app reads `tones`.
    """

    id: str
    label: str
    tones: dict[str, int] = Field(default_factory=dict)
    red: int
    amber: int
    green: int


class Performance(BaseModel):
    """The performance charts for one exam. `exam_code` is null only when the caller named
    no exam and has never attempted one."""

    exam_code: str | None = None
    summary: PerformanceSummary
    domains: list[DomainScore] = Field(default_factory=list)
    trend: list[TrendPoint] = Field(default_factory=list)
    composition: list[DomainComposition] = Field(default_factory=list)
    # How the exam's current rubric reads a mark: aggregates, pass lines, tones, bands and
    # labels (`rubrics.domain.resolved_display`). Pass lines are drawn from this.
    display: dict[str, Any] | None = None
    rating: RatingRead | None = None
    # True when the attempts shown were scored under more than one rubric version.
    mixed_versions: bool = False
    rubric_versions: int = 0


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
    # The slot was taken but could not be marked; the school has been told (T-3).
    # No attempt is linked, so no transcript is offered.
    marking_failed: bool = False
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
    # This rotation's own start (the sitting's start plus the circuit's stagger); null when undated.
    starts_at: datetime | None = None
    start_offset_minutes: int = 0
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
    # An exam sitting's result has been released to this person (T-5); false for practice, which has none.
    released: bool = False
    # Every station of theirs on this circuit was skipped and none was sat: absent, as a supervisor
    # recorded or because the circuit moved on without them.
    marked_absent: bool = False
    # Their connection to the station ended while its clock still runs; a supervisor can let them back in.
    waiting_for_rejoin: bool = False
    slots: list[MySlot] = Field(default_factory=list)


class MySittings(BaseModel):
    """The trainee portal's whole screen, in one request: what they are rostered onto."""

    items: list[MySitting] = Field(default_factory=list)


# --- What `/me/achievements` answers.


class StreakRead(BaseModel):
    length: int
    start_date: date
    end_date: date


class AchievementsRead(BaseModel):
    """A person's practice record, computed from their whole marked history."""

    station_count: int
    current_streak: int
    streak_badge_count: int
    longest_streak: StreakRead | None = None


# --- The account directory: what the platform console lists about everybody.


class DirectoryUser(BaseModel):
    """One row of the account directory."""

    id: uuid.UUID
    email: str
    name: str
    created_at: datetime
    status: str
    is_platform_admin: bool
    exam_code: str | None
    last_login_at: datetime | None
    # A refresh chain neither expired nor revoked — the old "Online" column.
    signed_in: bool
    # Any payment at all. The old `has_paid`.
    has_paid: bool
    # What the most recent payment bought, and when it was made.
    plan_code: str | None
    last_paid_at: datetime | None
    # The furthest end of any live grant, or None for open-ended or nothing.
    access_ends_at: datetime | None
    live_exam_codes: list[str] = Field(default_factory=list)
    attempt_count: int


class ExamDirectorySummary(BaseModel):
    """How many accounts an exam has, split by paid/trial/not-started."""

    code: str
    name: str
    users: int
    paid: int
    trial: int
    not_started: int


class DirectorySummary(BaseModel):
    exams: list[ExamDirectorySummary]
    # Accounts naming no exam and holding no live grant, and how many of them
    # paid (a payment whose grant has lapsed) or are on trial.
    unassigned: int
    unassigned_paid: int
    unassigned_trial: int
    total: int
    # Every account with a payment / every unpaid one that has started, whatever
    # exam it names: the same people the `access=paid` / `access=trial` facet lists.
    paid: int
    trial: int
