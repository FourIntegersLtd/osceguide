"""What a slot's reviews add up to.

Split from `service.py` along the direction of the work: that module records
judgement — a reviewer submits, a GP lead signs, a circuit is finalised — and
this one reads it back and combines it. The combining is the part that was
missing: `combine_rag` was written, unit-tested and called by nothing, so every
screen that showed a slot's rating worked it out for itself.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.reviews import domain, repository, scoring
from app.features.reviews.schemas import SlotRagSummary, SlotReviewsRead
from app.features.reviews.service import _slot_read


async def read_slot_reviews(session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID) -> SlotReviewsRead:
    """Every review of one slot, and what they add up to.

    The aggregate used to be the browser's job, which meant the console, a
    released result and anything exported could each compute it differently —
    and `combine_rag`, the rule that says how, had no caller at all.
    """
    rows = await repository.slot_reviews(session, org_id, slot_id)
    completed = [r for r in rows if r.status == "completed"]
    return SlotReviewsRead(
        items=[_slot_read(r) for r in rows],
        summary=_rag_summary(slot_id, [dict(r.field_values or {}) for r in completed]),
    )


async def summaries_for_slots(
    session: AsyncSession, org_id: uuid.UUID, slot_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, SlotRagSummary]:
    """What each slot's reviews add up to, read in one query.

    For the sitting report, which shows every candidate's every station: the
    per-slot read is right for one slot and wrong for six hundred.
    """
    by_slot = await repository.slot_reviews_for_slots(session, org_id, slot_ids)
    return {
        slot_id: _rag_summary(slot_id, [dict(r.field_values or {}) for r in rows if r.status == "completed"])
        for slot_id, rows in by_slot.items()
    }


def _rag_summary(slot_id: uuid.UUID, completed: list[dict[str, Any]]) -> SlotRagSummary:
    ratings: dict[str, list[str]] = {}
    for field_values in completed:
        for path, value in field_values.items():
            if not path.endswith(".score") or not isinstance(value, str):
                continue
            ratings.setdefault(path.split(".", 1)[0], []).append(value)

    by_domain: dict[str, str] = {}
    for domain_name, values in ratings.items():
        try:
            combined = domain.combine_rag(values)
        except domain.InvalidRag:
            # A stored value outside the vocabulary is a migration artefact,
            # not something a reader should be handed a 500 for. The domain is
            # reported as unrated rather than guessed at.
            continue
        if combined is not None:
            by_domain[domain_name] = combined

    return SlotRagSummary(
        slot_id=slot_id,
        overall_rag=domain.combine_rag(list(by_domain.values())),
        by_domain=dict(sorted(by_domain.items())),
        completed_reviews=len(completed),
    )


def combine_ratings(values: Sequence[str | None]) -> str | None:
    """The worst of several ratings, or None if nothing is rated.

    The same rule `_rag_summary` applies within one slot, exposed because a
    caller with several slots — a candidate's stations across a sitting —
    must not reach into this slice's domain to reimplement it.
    """
    try:
        return domain.combine_rag([v for v in values if v])
    except domain.InvalidRag:
        # A stored value outside the vocabulary is a migration artefact, not
        # something a reader should be handed a 500 for.
        return None


def score_for_ratings(values: Sequence[str]) -> float | None:
    """The 0–100 score a set of competency ratings adds up to.

    The majority rating rather than the mean — three greens and a red is a
    green with a red in it, not an amber that describes neither — and ties
    resolved downward. Exposed for the same reason `combine_ratings` is: the
    learner's own dashboard scores the marking engine's output, and it must not
    reimplement the arithmetic an institution ranks its cohort on. A rating
    outside the vocabulary leaves the set unscored rather than raising.
    """
    try:
        majority = scoring.majority_rag(list(values))
    except domain.InvalidRag:
        return None
    return scoring.RAG_SCORES[majority] if majority is not None else None


def mean_score(values: Sequence[float]) -> float | None:
    """Several domain scores as one, equally weighted.

    `scoring.station_score` over a bare sequence: a domain with twelve
    competencies counts the same as one with four, which is a decision worth
    stating rather than leaving in an average.
    """
    return scoring.station_score({str(i): v for i, v in enumerate(values)})


async def scores_for_slots(
    session: AsyncSession, org_id: uuid.UUID, slot_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, float | None]:
    """The effective score of each slot, after any GP-lead review.

    Exposed for the cohort summary, which ranks a sitting's candidates on
    these. The effective score is what a reviewer left standing, not what the
    marking said — `apply_review_overrides` is where the difference lives.
    """
    by_slot = await repository.slot_reviews_for_slots(session, org_id, slot_ids)
    gp_leads = await repository.gp_lead_reviews_for_slots(session, org_id, slot_ids)
    out: dict[uuid.UUID, float | None] = {}
    for slot_id in slot_ids:
        marked: dict[str, object] = {}
        for row in by_slot.get(slot_id, []):
            if row.status == "completed":
                marked.update(dict(row.field_values or {}))
        gp_lead = gp_leads.get(slot_id)
        reviewed = dict(gp_lead.field_values or {}) if gp_lead else {}
        out[slot_id] = scoring.station_score(scoring.apply_review_overrides(marked, reviewed))
    return out


def review_priority(*, completion_rate: float, assessment_score: float | None) -> str:
    """Which candidates a reviewer should look at first.

    The rule is `scoring.review_priority`; this is the public face of it, so a
    caller outside this slice asks the service rather than reaching past it
    into the arithmetic. `reviews` owns what a rating means.
    """
    return scoring.review_priority(completion_rate=completion_rate, assessment_score=assessment_score)
