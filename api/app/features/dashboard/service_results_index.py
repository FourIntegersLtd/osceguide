"""The results index: every sitting with how far its decisions have got."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.dashboard.schemas_org import ResultsIndex, ResultsIndexRow
from app.features.results import service as results
from app.features.roster import service as roster
from app.features.sittings import service_reads as sittings

CANCELLED = "cancelled"


async def build_results_index(session: AsyncSession, org_id: uuid.UUID, *, limit: int = 200) -> ResultsIndex:
    """Non-cancelled sittings, newest first, each with candidates by decision stage."""
    recent, truncated = await sittings.recent_sittings_page(
        session, org_id, limit=limit, exclude_status=CANCELLED
    )
    ids = [sitting.id for sitting in recent]
    candidates = await sittings.candidate_counts(session, org_id, ids)
    # Decisions are append-only: count only those of people still on a circuit (users -> roster ids).
    on_circuits = await sittings.candidate_user_ids(session, org_id, ids)
    roster_ids = await roster.trainees_by_user_id(
        session, org_id, sorted({user for users in on_circuits.values() for user in users})
    )
    decisions = await results.decision_counts(
        session,
        org_id,
        {
            sid: {roster_ids[user].id for user in on_circuits.get(sid, set()) if user in roster_ids}
            for sid in ids
        },
    )
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
    return ResultsIndex(rows=rows, truncated=truncated)
