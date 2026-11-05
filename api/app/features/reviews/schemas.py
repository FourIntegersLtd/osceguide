"""What the reviews routes accept and return: slot reviews, the GP-lead review,
and a circuit's finalised review."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.core.schemas import RatingRead, RatingValueRead, ReviewFormRead


class SlotReviewRead(BaseModel):
    id: uuid.UUID
    slot_id: uuid.UUID
    submitted_by: uuid.UUID
    observer_trainee_id: uuid.UUID | None
    status: str
    field_values: dict[str, Any]
    notes: str | None
    completed_at: datetime | None
    # Who finished this review and what it rated overall, as the exam-day board shows them. Null on
    # a draft: a half-written judgement is not attributed to anyone.
    reviewer_name: str | None = None
    overall: RatingValueRead | None = None
    # What the reviewer can rate, from the sitting's rubric; null if the slot has none.
    form: ReviewFormRead | None = None


class MarkingRetryRead(BaseModel):
    """What asking for a slot's automatic marking again answered: whether it was queued, and why not."""

    queued: bool
    policy_version: str
    reason: str | None = None


class SlotRagSummary(BaseModel):
    """What several reviewers of one slot agreed, or did not, in the rubric's own rating.

    Per domain, every completed review's ratings in it combine as one
    (`rubrics.scoring.combine_reviewers`: the majority, ties to the worse).
    The overall is the worst domain: one weak domain is what a reader must see.
    The name keeps `rag` until the web app reads the rubric's own rating fields.
    """

    slot_id: uuid.UUID
    # Null when nothing has been completed yet: no reviews, or only drafts.
    overall_rag: RatingValueRead | None = None
    by_domain: dict[str, RatingValueRead] = Field(default_factory=dict)
    # Each `by_domain` id's human title, from the rubric's own structure
    # (`rubrics.service.domain_titles`), so a reader never has to humanise an
    # id itself. Empty when the slot has no rubric, or the id names no domain
    # the structure still declares.
    domain_labels: dict[str, str] = Field(default_factory=dict)
    completed_reviews: int = 0
    # How to read the values above; null when the slot has no rubric.
    rating: RatingRead | None = None
    # 0-100: each domain's combined rating as a share of the best, averaged.
    score: float | None = None
    # By the rubric's pass rule; null when it sets none or nothing is rated.
    passed: bool | None = None


class SlotReviewsRead(BaseModel):
    items: list[SlotReviewRead] = Field(default_factory=list)
    summary: SlotRagSummary
    # What a reviewer can rate on this slot, from the sitting's rubric.
    form: ReviewFormRead | None = None
    # Whether every finished review rated the station the same overall; null with fewer than two.
    reviewers_agree: bool | None = None
    # Why the slot's last attempt failed when it has no live one (`no_marking_rubric`): the
    # station was taken, so "nobody took it" would be untrue. Null otherwise.
    attempt_failed_reason: str | None = None


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
    # The GP lead's own overall verdict: always G, A or R, whatever the rubric rates in.
    overall_rag: str | None
    field_values: dict[str, Any]
    notes: str | None
    completed_at: datetime | None
    # What the GP lead can rate, from the sitting's rubric; null if the slot has none.
    form: ReviewFormRead | None = None


class SaveGpLeadReview(BaseModel):
    """`revision` is what the client last read.

    Required, so a client that does not send it cannot overwrite blindly.
    """

    revision: int = Field(ge=0)
    field_values: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None
    overall_rag: str | None = None
    status: str = Field(default="draft")


class MySlotReviewRead(BaseModel):
    """A candidate's own read of their slot's review: the RAG summary and the
    GP-lead's written feedback, once one has been completed. Never a
    reviewer's draft, and never who observed them."""

    slot_id: uuid.UUID
    state: Literal["ready"] = "ready"
    summary: SlotRagSummary
    notes: str | None
    completed_at: datetime | None


class MySlotReviewWaiting(BaseModel):
    """Why a candidate has no review to read yet (T-8): the result is not released, or not marked."""

    slot_id: uuid.UUID
    state: Literal["not_released", "not_marked"]


class CircuitReviewRead(BaseModel):
    id: uuid.UUID
    circuit_id: uuid.UUID
    merged_notes: str | None
    finalized_at: datetime | None
    finalized_by: uuid.UUID | None = None


class FinalizeCircuitReview(BaseModel):
    merged_notes: str | None = None
