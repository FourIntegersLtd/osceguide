"""The results index: every sitting with how far its decisions have got."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.dashboard.schemas_org import ResultsIndex, ResultsIndexRow
from app.features.results import service as results
from app.features.sittings import service_reads as sittings

CANCELLED = "cancelled"


async def build_results_index(session: AsyncSession, org_id: uuid.UUID, *, limit: int = 200) -> ResultsIndex:
    """Non-cancelled sittings, newest first, each with candidates by decision stage."""
    recent = await sittings.recent_sittings(session, org_id, limit=limit, exclude_status=CANCELLED)
    candidates = await sittings.candidate_counts(session, org_id, [sitting.id for sitting in recent])
    decisions = await results.decision_counts(session, org_id, [sitting.id for sitting in recent])
    rows: list[ResultsIndexRow] = []
    for sitting in recent:
        stages = decisions.get(sitting.id, {})
        draft, signed_off, released = (stages.get(state, 0) for state in ("draft", "signed_off", "released"))
        total = candidates.get(sitting.id, 0)
        rows.append(
            ResultsIndexRow(
                sitting_id=sitting.id,
                name=sitting.name,
                mode=sitting.mode,
                status=sitting.status,
                scheduled_for=sitting.scheduled_for,
                candidates=total,
                not_decided=max(total - (draft + signed_off + released), 0),
                draft=draft,
                signed_off=signed_off,
                released=released,
            )
        )
    return ResultsIndex(rows=rows)
