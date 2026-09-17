"""What a slot's reviews add up to.

Split from `service.py` along the direction of the work: that module records
judgement — a reviewer submits, a GP lead signs, a circuit is finalised — and
this one reads it back and combines it. The combining is the part that was
missing: `combine_rag` was written, unit-tested and called by nothing, so every
screen that showed a slot's rating worked it out for itself.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.reviews import domain, repository
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
