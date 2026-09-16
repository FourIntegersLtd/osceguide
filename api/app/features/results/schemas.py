from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DecisionRead(BaseModel):
    revision: int
    workflow_state: str
    assessment_outcome: str | None
    recruitment_outcome: str | None
    rationale: str | None
    signed_off_at: datetime | None
    released_at: datetime | None


class SaveDecision(BaseModel):
    assessment_outcome: str | None = Field(default=None, pattern="^(pass|fail|inconclusive|withheld)$")
    recruitment_outcome: str | None = Field(
        default=None, pattern="^(hired|reserve|not_hired|withdrawn|pending)$"
    )
    rationale: str | None = Field(default=None, max_length=4000)
    moderation_notes: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class TraineeResultRead(BaseModel):
    """What a candidate sees.

    Deliberately narrower than the internal record: moderation notes and the
    evidence snapshot are ours, not theirs. b2b's own schema doc says not to
    reproduce disclosure policy in frontend transforms — so it is applied here.
    """

    sitting_id: uuid.UUID
    assessment_outcome: str | None
    rationale: str | None
    released_at: datetime | None
