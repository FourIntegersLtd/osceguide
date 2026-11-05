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
    figures = await sittings.programme_figures(
        session, org_id, outcomes_by_sitting=await results.released_outcomes_by_sitting(session, org_id)
    )
    rows: list[ProgrammeReportRow] = []
    for programme in programmes:
        figure = figures.get(programme.id, sittings.ProgrammeFigures(0, 0, 0, 0))
        rows.append(
            ProgrammeReportRow(
                programme_id=programme.id,
                exam_id=programme.exam_id,
                exam_name=programme.exam_name,
                sittings=figure.sittings,
                candidates=figure.candidates,
                released=figure.released,
                passed=figure.passed,
                pass_rate=round(100 * figure.passed / figure.released, 1) if figure.released else None,
            )
        )
    return OrgReporting(programmes=rows)
