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
