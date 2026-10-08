"""What the platform console reads about an attempt.

Separate from `schemas.py`: those are what a candidate sees of their own
attempt, and none of them say whose it is, why it failed, or whether the
marking is queued, running or lost. Support needs exactly those.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.features.attempts.schemas import AttemptRead


class ScoringJobRead(BaseModel):
    """One marking job as the queue holds it."""

    id: int
    status: str
    attempts: int
    policy_version: str | None
    scheduled_at: datetime | None


class PlatformAttemptRead(AttemptRead):
    """An attempt, with the state a support question turns on.

    `scoring_job` is the newest marking job for it, or None when nothing was
    ever queued — which with a complete transcript is itself the diagnosis.
    """

    user_id: uuid.UUID
    org_id: uuid.UUID | None
    failed_reason: str | None
    transcript_complete: bool
    transcript_delivered_at: datetime | None
    result_policy_versions: list[str]
    scoring_job: ScoringJobRead | None


class PlatformAttemptDetail(PlatformAttemptRead):
    has_definition: bool
    definition_frozen_at: datetime | None
    chunk_count: int
    jobs: list[ScoringJobRead]
    # For an exam_slot attempt: the sitting it was sat in. None for every other kind.
    sitting_id: uuid.UUID | None = None
    sitting_name: str | None = None


class RescoreRequest(BaseModel):
    """Re-queue the marking. Left empty, under the policy the attempt was
    frozen with; named, under another one, whose result sits beside the old."""

    policy_version: str | None = Field(default=None, min_length=1, max_length=128)


class RescoreResult(BaseModel):
    queued: bool
    policy_version: str
    reason: str | None = None


class FailAttemptRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=180)
