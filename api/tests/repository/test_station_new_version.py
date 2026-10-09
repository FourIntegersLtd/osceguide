"""A new version of a published station keeps the template its content was written against."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.stations import repository as stations_repo
from app.features.stations import repository_templates as templates_repo
from app.features.stations import service_versions
from app.features.stations.models import StationVersion
from tests.support.catalog import ensure_exam

pytestmark = pytest.mark.db

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
CONTENT = {"management_plan": {"assessment": "Ottawa knee rules first."}}


async def test_a_new_version_keeps_the_published_versions_template(db_session: AsyncSession) -> None:
    exam = await ensure_exam(db_session, "ortho")
    assert exam is not None
    template = await templates_repo.create_template(db_session, None, exam_id=exam.id, title="Ortho")
    template_version = await templates_repo.add_template_version(
        db_session, None, template_id=template.id, version=1, structure={"sections": []}
    )
    station = await stations_repo.create_station(db_session, None, exam_id=exam.id, title="Knee injury")
    first = await stations_repo.add_version(
        db_session,
        None,
        station_id=station.id,
        version=1,
        content=CONTENT,
        template_version_id=template_version.id,
    )
    await stations_repo.set_version_status(db_session, None, first.id, status="published", at=NOW, by=None)
    await db_session.flush()

    draft = await service_versions.add_version(db_session, None, station.id)

    assert draft.version == 2
    stored = await db_session.get(StationVersion, draft.id)
    assert stored is not None
    assert stored.template_version_id == template_version.id
