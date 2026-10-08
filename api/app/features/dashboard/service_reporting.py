"""Reporting across sittings: a projection of figures other slices already hold."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog import service_programmes
from app.features.dashboard.schemas_reporting import OrgReporting, ProgrammeReportRow
from app.features.results import service as results
from app.features.sittings import service_reads as sittings

_MOST_PROGRAMMES = 200


async def build_org_reporting(session: AsyncSession, org_id: uuid.UUID) -> OrgReporting:
    """Per programme: sittings, candidates and the pass rate of released decisions."""
    programmes, _ = await service_programmes.list_programmes(
        session, org_id, limit=_MOST_PROGRAMMES, cursor=None
    )
    activity = await sittings.programme_activity(session, org_id)
    programme_of = await sittings.sitting_programmes(session, org_id)
    released: dict[uuid.UUID, int] = {}
    passed: dict[uuid.UUID, int] = {}
    for sitting_id, outcomes in (await results.released_outcomes_by_sitting(session, org_id)).items():
        programme_id = programme_of.get(sitting_id)
        if programme_id is None:
            continue
        released[programme_id] = released.get(programme_id, 0) + len(outcomes)
        wins = sum(1 for outcome in outcomes if outcome == "pass")
        passed[programme_id] = passed.get(programme_id, 0) + wins
    rows: list[ProgrammeReportRow] = []
    for programme in programmes:
        held, people = activity.get(programme.id, (0, 0))
        decided = released.get(programme.id, 0)
        rows.append(
            ProgrammeReportRow(
                programme_id=programme.id,
                exam_name=programme.exam_name,
                sittings=held,
                candidates=people,
                released=decided,
                passed=passed.get(programme.id, 0),
                pass_rate=round(100 * passed.get(programme.id, 0) / decided, 1) if decided else None,
            )
        )
    return OrgReporting(programmes=rows)
