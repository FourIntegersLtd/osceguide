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

from app.features.attempts.schemas_material import PatientReviewRead


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


class PatientRoleplayRead(PatientReviewRead):
    opening_sentence: str | None = None
    expanded_history: str | None = None
    persona: str | None = None
    family_social_history: list[str] = Field(default_factory=list)
    past_med_history_allergies: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)


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
