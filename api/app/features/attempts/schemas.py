"""The API and worker contracts for attempts.

The worker-facing shapes mirror `osce_assessment.contracts`: the worker
validates what we send as `AssessmentAttempt` and `Scenario`, so these are the
backend's side of a contract owned elsewhere, not free choices.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


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
