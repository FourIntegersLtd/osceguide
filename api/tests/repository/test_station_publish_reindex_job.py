"""Publishing or archiving a library station queues the tutor's re-index in the same transaction."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.identity import repository as identity_repo
from app.features.stations import repository as stations_repo
from app.features.stations import service_versions
from app.features.tenancy import repository as tenancy_repo
from tests.support.catalog import ensure_exam

pytestmark = pytest.mark.db

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)
CONTENT = {"management_plan": {"assessment": "Rule out an acute coronary syndrome first."}}


async def queued_reindexes(db_session: AsyncSession) -> int:
    count = await db_session.scalar(
        text(
            "SELECT count(*) FROM procrastinate_jobs WHERE task_name = 'reindex_material' AND status = 'todo'"
        )
    )
    return int(count or 0)


async def draft_station(db_session: AsyncSession, org_id: uuid.UUID | None) -> tuple[uuid.UUID, uuid.UUID]:
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    author = await identity_repo.create_user(
        db_session, email=f"s{uuid.uuid4().hex[:8]}@example.com", name="Author", password_hash=None
    )
    station = await stations_repo.create_station(db_session, org_id, exam_id=exam.id, title="Chest pain")
    await stations_repo.add_version(db_session, org_id, station_id=station.id, version=1, content=CONTENT)
    await db_session.flush()
    return station.id, author.id


async def test_publishing_then_archiving_a_library_station_queues_one_reindex(
    db_session: AsyncSession,
) -> None:
    before = await queued_reindexes(db_session)
    station_id, author_id = await draft_station(db_session, None)

    await service_versions.publish_version(db_session, None, station_id, 1, actor_id=author_id, now=NOW)
    after_publish = await queued_reindexes(db_session)
    await service_versions.archive_version(db_session, None, station_id, 1, actor_id=author_id, now=NOW)

    assert after_publish == max(before, 1)
    # A walk still waiting covers the archive too: the two changes share it.
    assert await queued_reindexes(db_session) == after_publish


async def test_an_organisations_own_station_queues_nothing(db_session: AsyncSession) -> None:
    org = await tenancy_repo.create_organization(db_session, name="Trust", slug=f"t{uuid.uuid4().hex[:8]}")
    before = await queued_reindexes(db_session)
    station_id, author_id = await draft_station(db_session, org.id)

    await service_versions.publish_version(db_session, org.id, station_id, 1, actor_id=author_id, now=NOW)

    assert await queued_reindexes(db_session) == before
