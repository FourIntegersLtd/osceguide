"""What a slot's reviews add up to: reads reviews back and combines them.

Every rating is read in the sitting's rubric's own units (`rubrics.scoring`):
a review of an R/A/G rubric combines to R/A/G, a 0-10 rubric to a number.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import service_reads as attempts
from app.features.reviews import errors, repository, scoring
from app.features.reviews.schemas import (
    MySlotReviewRead,
    MySlotReviewWaiting,
    SlotRagSummary,
    SlotReviewsRead,
)
from app.features.reviews.service import _slot_read, review_form, slot_rubric
from app.features.rubrics import service_marking as rubrics
from app.features.rubrics import service_scoring as rubric_scoring
from app.features.sittings import service as sittings
from app.features.sittings import service_reads as sittings_reads


@dataclass(frozen=True)
class SlotOutcome:
    """What a slot's reviews leave standing, after any GP-lead review."""

    # 0-100: each domain's combined rating as a share of the best, averaged. None if unrated.
    score: float | None
    # By the rubric's pass rule; None when it sets none or nothing is rated.
    passed: bool | None


async def read_my_slot_review(
    session: AsyncSession, *, slot_id: uuid.UUID, user_id: uuid.UUID
) -> MySlotReviewRead | MySlotReviewWaiting:
    """A candidate's own read of their slot's review; says why there is none to share yet.

    A training slot's review is shared the moment a reviewer completes it: practice has no
    sign-off or release (R-36). An exam slot's feeds the decision, so it waits for the result
    to be released and the GP lead to complete a review. Refused as "not found" rather than
    "forbidden" if the slot is not this person's own.
    """
    # `results` imports this module, so its import has to wait until call time.
    from app.features.results import service_candidate as results_candidate

    pair = await sittings.slot_and_circuit_for_owner(session, slot_id, user_id)
    if pair is None:
        raise errors.SlotNotFound()
    slot, circuit = pair
    found = await sittings_reads.slot_and_sitting(session, slot.org_id, slot_id)
    reviews = await repository.slot_reviews(session, slot.org_id, slot_id)
    completed = [review for review in reviews if review.status == "completed"]

    if found is not None and found[1].mode != "exam":
        if not completed:
            return MySlotReviewWaiting(slot_id=slot_id, state="not_marked")
        notes = "\n\n".join(review.notes for review in completed if review.notes) or None
        completed_at = max((review.completed_at for review in completed if review.completed_at), default=None)
    else:
        if await results_candidate.read_my_result(session, circuit.sitting_id, user_id) is None:
            return MySlotReviewWaiting(slot_id=slot_id, state="not_released")
        lead_review = await repository.gp_lead_review(session, slot.org_id, slot_id)
        if lead_review is None or lead_review.status != "completed":
            return MySlotReviewWaiting(slot_id=slot_id, state="not_marked")
        notes, completed_at = lead_review.notes, lead_review.completed_at

    scoring_rubric = await slot_rubric(session, slot.org_id, slot_id)
    summary = _summary(slot_id, scoring_rubric, [dict(review.field_values or {}) for review in completed])
    return MySlotReviewRead(slot_id=slot_id, summary=summary, notes=notes, completed_at=completed_at)


async def slots_with_pending_reviews(
    session: AsyncSession, org_id: uuid.UUID, slot_ids: Sequence[uuid.UUID]
) -> set[uuid.UUID]:
    """Which of these slots have a review, or a GP-lead review, still a draft (R-33)."""
    by_slot = await repository.slot_reviews_for_slots(session, org_id, slot_ids)
    pending = {slot_id for slot_id, rows in by_slot.items() if any(row.status != "completed" for row in rows)}
    lead = await repository.gp_lead_reviews_for_slots(session, org_id, slot_ids)
    return pending | {slot_id for slot_id, row in lead.items() if row.status != "completed"}


async def read_slot_reviews(session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID) -> SlotReviewsRead:
    """Every review of one slot, and what they add up to."""
    reviews = await repository.slot_reviews(session, org_id, slot_id)
    completed = [review for review in reviews if review.status == "completed"]
    scoring_rubric = await slot_rubric(session, org_id, slot_id)
    return SlotReviewsRead(
        items=[_slot_read(review) for review in reviews],
        summary=_summary(slot_id, scoring_rubric, [dict(review.field_values or {}) for review in completed]),
        form=review_form(scoring_rubric),
        attempt_failed_reason=await attempts.failed_reason_for_slot(session, slot_id),
    )


async def summaries_for_slots(
    session: AsyncSession, org_id: uuid.UUID, slot_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, SlotRagSummary]:
    """What each slot's reviews add up to, read in one query (for the sitting
    report, which shows every candidate's every station)."""
    by_slot = await repository.slot_reviews_for_slots(session, org_id, slot_ids)
    rubrics_by_slot = await _rubrics_for_slots(session, org_id, slot_ids)
    return {
        slot_id: _summary(
            slot_id,
            rubrics_by_slot.get(slot_id),
            [dict(review.field_values or {}) for review in reviews if review.status == "completed"],
        )
        for slot_id, reviews in by_slot.items()
    }


async def _rubrics_for_slots(
    session: AsyncSession, org_id: uuid.UUID, slot_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, rubrics.ScoringRubric]:
    """Each slot's scoring rubric, reading each distinct version once (a sitting binds one)."""
    version_by_slot = await sittings.rubric_versions_for_slots(session, org_id, slot_ids)
    by_version: dict[uuid.UUID, rubrics.ScoringRubric] = {}
    for version_id in set(version_by_slot.values()):
        by_version[version_id] = await rubrics.scoring_rubric_for_version(session, org_id, version_id)
    return {slot_id: by_version[version_id] for slot_id, version_id in version_by_slot.items()}


def _summary(
    slot_id: uuid.UUID, scoring_rubric: rubrics.ScoringRubric | None, completed: list[dict[str, Any]]
) -> SlotRagSummary:
    """What a slot's completed reviews add up to: one combined rating per domain, the worst overall.

    Every reviewer's ratings in a domain are combined as one
    (`combine_reviewers`); a rating that is not one on this rubric (a
    migration artefact) is skipped rather than guessed at.
    """
    if scoring_rubric is None:
        return SlotRagSummary(slot_id=slot_id, completed_reviews=len(completed))
    structure = scoring_rubric.structure
    ratings_by_domain: dict[str, list[rubric_scoring.RatingValue]] = {}
    for field_values in completed:
        for domain_id, ratings in rubric_scoring.ratings_from_paths(structure, field_values).items():
            ratings_by_domain.setdefault(domain_id, []).extend(ratings)

    by_domain: dict[str, rubric_scoring.RatingValue] = {}
    for domain_id, ratings in sorted(ratings_by_domain.items()):
        combined = rubric_scoring.combine_reviewers(structure, ratings)
        if combined is not None:
            by_domain[domain_id] = combined

    return SlotRagSummary(
        slot_id=slot_id,
        overall_rag=rubric_scoring.worst_rating(structure, list(by_domain.values())),
        by_domain=by_domain,
        # Every domain the rubric declares, not only the ones rated here: a
        # reader may want to show an unrated domain too. `structure` is
        # already the parsed `RubricStructure` (via `parse_structure`), so
        # this reads its `.domains` convenience property, never a raw dict.
        domain_labels={section.id: section.title for section in structure.domains},
        completed_reviews=len(completed),
        rating=rubrics.rating_read(structure),
        score=scoring.station_score(scoring.scores_by_domain(structure, ratings_by_domain)),
        passed=rubric_scoring.passed(structure, scoring_rubric.display, ratings_by_domain),
    )


async def outcomes_for_slots(
    session: AsyncSession, org_id: uuid.UUID, slot_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, SlotOutcome]:
    """The effective score and pass of each slot, after any GP-lead review.

    The effective ratings are what a reviewer left standing, not what the
    marking said — see `scoring.effective_ratings`. A slot with no rubric, or
    no rating, has neither.
    """
    by_slot = await repository.slot_reviews_for_slots(session, org_id, slot_ids)
    gp_leads = await repository.gp_lead_reviews_for_slots(session, org_id, slot_ids)
    rubrics_by_slot = await _rubrics_for_slots(session, org_id, slot_ids)
    outcomes: dict[uuid.UUID, SlotOutcome] = {}
    for slot_id in slot_ids:
        scoring_rubric = rubrics_by_slot.get(slot_id)
        if scoring_rubric is None:
            outcomes[slot_id] = SlotOutcome(score=None, passed=None)
            continue
        marked: dict[str, object] = {}
        for review in by_slot.get(slot_id, []):
            if review.status == "completed":
                marked.update(dict(review.field_values or {}))
        gp_lead = gp_leads.get(slot_id)
        reviewed = dict(gp_lead.field_values or {}) if gp_lead else {}
        effective = scoring.effective_ratings(scoring_rubric.structure, marked, reviewed)
        outcomes[slot_id] = SlotOutcome(
            score=scoring.station_score(scoring.scores_by_domain(scoring_rubric.structure, effective)),
            passed=rubric_scoring.passed(scoring_rubric.structure, scoring_rubric.display, effective),
        )
    return outcomes


def review_priority(*, completion_rate: float, assessment_score: float | None) -> str:
    """Which candidates a reviewer should look at first. See `scoring.review_priority`."""
    return scoring.review_priority(completion_rate=completion_rate, assessment_score=assessment_score)
