"""The API and worker contracts for attempts.

The worker-facing shapes mirror `osce_assessment.contracts`: the worker
validates what we send as `AssessmentAttempt` and `Scenario`, so these are the
backend's side of a contract owned elsewhere, not free choices.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.core.schemas import AudienceSectionRead, RatingRead, ResultTotalsRead

# Re-exported: `rubrics`' trial-candidates routes need the same shape, and a
# shape two slices' response models share lives in `core`, not in either
# slice's own `schemas.py` (`tests/guards/test_schemas_are_not_rows.py`).
from app.core.schemas import TrialCandidateRead as TrialCandidateRead


class TranscriptMessageIn(BaseModel):
    """One turn, exactly as `osce_assessment.contracts.TranscriptMessage`."""

    role: str
    message: str
    timestamp: datetime
    message_id: str
    seq: int = Field(ge=0)


class TranscriptIn(BaseModel):
    attempt_id: str
    messages: list[TranscriptMessageIn]
    complete: bool
    runtime_label: str | None = None


class ChunkPost(BaseModel):
    attempt_id: str
    message: TranscriptMessageIn


class TranscriptPost(BaseModel):
    attempt_id: str
    transcript: TranscriptIn


class WorkerAccepted(BaseModel):
    status: str = "accepted"


class WorkerBootstrap(BaseModel):
    """`{attempt, scenario}` — the only thing a worker is told.

    Both halves are passed through as the engine's own documents rather than
    re-modelled here: re-describing them would create a second definition of a
    contract the engine already owns, free to drift.
    """

    attempt: dict[str, Any]
    scenario: dict[str, Any]


class TranscriptMessageRead(BaseModel):
    role: str
    message: str
    seq: int
    spoken_at: datetime


class TranscriptRead(BaseModel):
    attempt_id: uuid.UUID
    complete: bool
    messages: list[TranscriptMessageRead]


class AssessmentResultRead(BaseModel):
    framework_id: str
    policy_version: str
    model_used: str | None
    payload: dict[str, Any]
    scored_at: datetime


class MarkingRubricRead(BaseModel):
    """The rubric an attempt was marked with, frozen on it: what a feedback screen draws from."""

    # The rubric version it was frozen from, when known.
    version_id: str | None
    # Version 2 structure JSON, narrowed to the domains this attempt was marked on.
    structure: dict[str, Any]
    # `rubrics.domain.resolved_display`: aggregates, pass lines, tones, bands and labels.
    display: dict[str, Any]
    rating: RatingRead


class MarkedResultRead(AssessmentResultRead):
    """One marked result, with the numbers its own rubric makes of it."""

    # Null when the attempt has no rubric to read the result by.
    totals: ResultTotalsRead | None = None


class AttemptFeedbackRead(BaseModel):
    """Everything a feedback screen needs: the frozen rubric, and each result with its totals.

    Results are oldest first; a re-marked attempt keeps both, and the last is current.
    """

    attempt_id: uuid.UUID
    # Null for an attempt no rubric can describe (nothing to draw it by).
    rubric: MarkingRubricRead | None
    results: list[MarkedResultRead] = Field(default_factory=list)


class AttemptRead(BaseModel):
    id: uuid.UUID
    kind: str
    status: str
    exam_id: uuid.UUID
    station_version_id: uuid.UUID | None
    room_name: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class CreateAttempt(BaseModel):
    """What a client may ask for directly.

    Deliberately narrower than `attempts.create_attempt`. The other kinds are *about* something a
    different feature owns — a slot, a set entry, a peer pairing, an earlier attempt. Taking those ids
    straight from the body unverified once let a caller attach their attempt to another organisation's
    exam slot or another person's set entry, so each of those kinds instead has its own route that
    checks ownership: `POST /me/station-sets/{set_id}/entries/{entry_id}/attempts` for a set station
    and its debrief, and the circuit itself for an exam slot (ADR 0018). `room_name` is likewise not
    the client's to choose — `voice` derives it from the attempt.
    """

    kind: str = Field(pattern="^(practice|self_practice)$")
    exam_code: str = Field(min_length=1, max_length=32)
    station_version_id: uuid.UUID | None = None


# --- Actor material available to the owner after a consultation finishes.


class PatientRoleplayRead(BaseModel):
    """The patient's whole script, for the candidate to play back once their own attempt has finished.

    The patient audience's sections, with `include_hidden=True`: the actor needs the ICE and the
    questions the patient holds back, not just what a candidate or an examiner may read of the same
    station.
    """

    sections: list[AudienceSectionRead] = Field(default_factory=list)


# --- Live coverage of an attempt.


class CoverageItemRead(BaseModel):
    competency_id: str
    label: str
    state: Literal["partial", "covered"]
    quote: str
    seq: int


class CoverageRead(BaseModel):
    supported: bool
    items: list[CoverageItemRead] = Field(default_factory=list)
    last_seq: int = -1


# --- A trial mark of a rubric version (plan §8, Stage 4).


class TrialMarkRequest(BaseModel):
    """What to mark: a pasted transcript, or one of the owner's own finished attempts. Exactly one."""

    # One turn per line, `Speaker: what they said`. Candidate, doctor, user,
    # you, trainee, student or clinician is the candidate; anyone else the
    # patient. A line with no speaker continues the turn before it.
    transcript: str | None = Field(default=None, max_length=200_000)
    attempt_id: uuid.UUID | None = None


class TrialMarkRead(BaseModel):
    """One snapshot of a trial mark: marking, then marked or failed. Nothing is stored."""

    status: Literal["marking", "marked", "failed"]
    elapsed_seconds: float
    rubric_version_id: uuid.UUID
    turn_count: int
    # What the marker wrote, validated by the version's result schema, once marked.
    marks: dict[str, Any] | None = None
    # `marks`' numbers by the version's own display rules.
    totals: ResultTotalsRead | None = None
    model_used: str | None = None
    # Why it failed, in the engine's words.
    error: str | None = None
