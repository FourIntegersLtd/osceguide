"""What a slot's reviews add up to: reads reviews back and combines them."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.reviews import domain, errors, repository, scoring
from app.features.reviews.schemas import MySlotReviewRead, SlotRagSummary, SlotReviewsRead
from app.features.reviews.service import _slot_read
from app.features.sittings import service as sittings


async def read_my_slot_review(
    session: AsyncSession, *, slot_id: uuid.UUID, user_id: uuid.UUID
) -> MySlotReviewRead:
    """A candidate's own read of their slot's review, once their result for the
    sitting is released and the GP lead has completed a review. Refused, as
    "not found" rather than "forbidden", if the slot is not this person's own
    or either is missing — the same privacy posture `SlotNotFound` uses."""
    # `results` imports this module, so its import has to wait until call time.
    from app.features.results import errors as results_errors  # noqa: PLC0415
    from app.features.results import service_candidate as results_candidate  # noqa: PLC0415

    pair = await sittings.slot_and_circuit_for_owner(session, slot_id, user_id)
    if pair is None:
        raise errors.ReviewNotFound()
    slot, circuit = pair
    # The review feeds the decision, so it stays hidden until the decision is released.
    try:
        await results_candidate.read_my_result(session, circuit.sitting_id, user_id)
    except results_errors.NotReleased as not_released:
        raise errors.ReviewNotFound() from not_released

    lead_review = await repository.gp_lead_review(session, slot.org_id, slot_id)
    if lead_review is None or lead_review.status != "completed":
        raise errors.ReviewNotFound()

    reviews = await repository.slot_reviews(session, slot.org_id, slot_id)
    completed = [review for review in reviews if review.status == "completed"]
    summary = _rag_summary(slot_id, [dict(review.field_values or {}) for review in completed])
    return MySlotReviewRead(
        slot_id=slot_id,
        summary=summary,
        notes=lead_review.notes,
        completed_at=lead_review.completed_at,
    )


async def read_slot_reviews(session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID) -> SlotReviewsRead:
    """Every review of one slot, and what they add up to."""
    reviews = await repository.slot_reviews(session, org_id, slot_id)
    completed = [review for review in reviews if review.status == "completed"]
    return SlotReviewsRead(
        items=[_slot_read(review) for review in reviews],
        summary=_rag_summary(slot_id, [dict(review.field_values or {}) for review in completed]),
    )


async def summaries_for_slots(
    session: AsyncSession, org_id: uuid.UUID, slot_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, SlotRagSummary]:
    """What each slot's reviews add up to, read in one query (for the sitting
    report, which shows every candidate's every station)."""
    by_slot = await repository.slot_reviews_for_slots(session, org_id, slot_ids)
    return {
        slot_id: _rag_summary(
            slot_id, [dict(review.field_values or {}) for review in reviews if review.status == "completed"]
        )
        for slot_id, reviews in by_slot.items()
    }


def _rag_summary(slot_id: uuid.UUID, completed: list[dict[str, Any]]) -> SlotRagSummary:
    """What a slot's completed reviews add up to, one rating per domain."""
    ratings_by_domain: dict[str, list[str]] = {}
    for field_values in completed:
        for path, rating in field_values.items():
            if not path.endswith(".score") or not isinstance(rating, str):
                continue
            ratings_by_domain.setdefault(path.split(".", 1)[0], []).append(rating)

    by_domain: dict[str, str] = {}
    for domain_name, domain_ratings in ratings_by_domain.items():
        try:
            combined = domain.combine_rag(domain_ratings)
        except domain.InvalidRag:
            # A value outside the vocabulary is a migration artefact; report
            # the domain as unrated rather than guess at it.
            continue
        if combined is not None:
            by_domain[domain_name] = combined

    return SlotRagSummary(
        slot_id=slot_id,
        overall_rag=domain.combine_rag(list(by_domain.values())),
        by_domain=dict(sorted(by_domain.items())),
        completed_reviews=len(completed),
    )


def combine_ratings(ratings: Sequence[str | None]) -> str | None:
    """The worst of several ratings, or None if nothing is rated."""
    try:
        return domain.combine_rag([rating for rating in ratings if rating])
    except domain.InvalidRag:
        # A value outside the vocabulary is a migration artefact, not an error.
        return None


def score_for_ratings(ratings: Sequence[str]) -> float | None:
    """The 0–100 score a set of competency ratings adds up to.

    The majority rating rather than the mean, ties resolved downward. A
    rating outside the vocabulary leaves the set unscored rather than raising.
    """
    try:
        majority = scoring.majority_rag(list(ratings))
    except domain.InvalidRag:
        return None
    return scoring.RAG_SCORES[majority] if majority is not None else None


def mean_score(scores: Sequence[float]) -> float | None:
    """Several domain scores as one, equally weighted."""
    return scoring.station_score({str(index): score for index, score in enumerate(scores)})


async def scores_for_slots(
    session: AsyncSession, org_id: uuid.UUID, slot_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, float | None]:
    """The effective score of each slot, after any GP-lead review.

    The effective score is what a reviewer left standing, not what the marking
    said — see `scoring.apply_review_overrides`.
    """
    by_slot = await repository.slot_reviews_for_slots(session, org_id, slot_ids)
    gp_leads = await repository.gp_lead_reviews_for_slots(session, org_id, slot_ids)
    scores: dict[uuid.UUID, float | None] = {}
    for slot_id in slot_ids:
        marked: dict[str, object] = {}
        for review in by_slot.get(slot_id, []):
            if review.status == "completed":
                marked.update(dict(review.field_values or {}))
        gp_lead = gp_leads.get(slot_id)
        reviewed = dict(gp_lead.field_values or {}) if gp_lead else {}
        scores[slot_id] = scoring.station_score(scoring.apply_review_overrides(marked, reviewed))
    return scores


def review_priority(*, completion_rate: float, assessment_score: float | None) -> str:
    """Which candidates a reviewer should look at first. See `scoring.review_priority`."""
    return scoring.review_priority(completion_rate=completion_rate, assessment_score=assessment_score)
