from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SlotReviewRead(BaseModel):
    id: uuid.UUID
    slot_id: uuid.UUID
    submitted_by: uuid.UUID
    observer_trainee_id: uuid.UUID | None
    status: str
    field_values: dict[str, Any]
    notes: str | None
    completed_at: datetime | None


class SlotRagSummary(BaseModel):
    """What several reviewers of one slot agreed, or did not.

    The worst rating wins per domain: when reviewers disagree, the lower
    rating is the one that should prompt a conversation.
    """

    slot_id: uuid.UUID
    # Null when nothing has been completed yet: no reviews, or only drafts.
    overall_rag: str | None = None
    by_domain: dict[str, str] = Field(default_factory=dict)
    completed_reviews: int = 0


class SlotReviewsRead(BaseModel):
    items: list[SlotReviewRead] = Field(default_factory=list)
    summary: SlotRagSummary


class SubmitSlotReview(BaseModel):
    field_values: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None
    status: str = Field(default="draft")
    observer_trainee_id: uuid.UUID | None = None


class GpLeadReviewRead(BaseModel):
    id: uuid.UUID
    slot_id: uuid.UUID
    revision: int
    status: str
    overall_rag: str | None
    field_values: dict[str, Any]
    notes: str | None
    completed_at: datetime | None


class SaveGpLeadReview(BaseModel):
    """`revision` is what the client last read.

    Required, so a client that does not send it cannot overwrite blindly.
    """

    revision: int = Field(ge=0)
    field_values: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None
    overall_rag: str | None = None
    status: str = Field(default="draft")


class CircuitReviewRead(BaseModel):
    id: uuid.UUID
    circuit_id: uuid.UUID
    merged_notes: str | None
    finalized_at: datetime | None


class FinalizeCircuitReview(BaseModel):
    merged_notes: str | None = None
