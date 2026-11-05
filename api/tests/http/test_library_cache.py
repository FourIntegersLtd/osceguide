"""The station library is read through the shared cache (`core.cache`), and every write that changes
what it shows makes the cached copy unreachable.

The library response carries nothing per person (id, title, exam code, version), so the page is
cached whole per exam; a plan-limited person's window differs per person and is never cached.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import cache
from app.core.auth import Principal
from app.features.catalog import service as catalog
from app.features.identity.models import User
from app.features.stations import repository_library, service_plan_window, service_versions
from app.features.stations import service as stations_service
from app.features.stations.models import Station
from tests.http.test_stations_routes import a_browser, a_library_station
from tests.support.catalog import ensure_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

_LIBRARY = "/api/v1/stations?exam_code=sca"


@pytest_asyncio.fixture
async def redis_cache(seat_redis: object, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[None]:
    """The cache pointed at the test Redis under a prefix no other test shares."""
    prefix = f"cachetest{uuid.uuid4().hex}"
    monkeypatch.setattr(cache, "get_redis", lambda: seat_redis)
    monkeypatch.setattr(cache, "KEY_PREFIX", prefix)
    yield
    keys = [key async for key in seat_redis.scan_iter(match=f"{prefix}:*")]  # type: ignore[attr-defined]
    if keys:
        await seat_redis.delete(*keys)  # type: ignore[attr-defined]


def _library_queries(statements: list[str]) -> list[str]:
    return [s for s in statements if "FROM stations" in s or "FROM station_versions" in s]


async def _titles(client: AsyncClient, token: str) -> list[str]:
    response = await client.get(_LIBRARY, headers=bearer(token))
    assert response.status_code == 200, response.text
    return [row["title"] for row in response.json()["items"]]


async def test_a_second_person_browsing_the_same_exam_runs_no_library_queries(
    client: AsyncClient, make_actor, db_session: AsyncSession, redis_cache: None
) -> None:  # type: ignore[no-untyped-def]
    first = await a_browser(db_session, make_actor, "first@example.com")
    second = await a_browser(db_session, make_actor, "second@example.com")
    await a_library_station(db_session, "Chest pain")

    primed = await _titles(client, first)
    statements: list[str] = []

    def record(conn, cursor, statement, *args):  # type: ignore[no-untyped-def]
        statements.append(statement)

    engine = db_session.bind.sync_engine  # type: ignore[union-attr]
    event.listen(engine, "before_cursor_execute", record)
    try:
        again = await _titles(client, second)
    finally:
        event.remove(engine, "before_cursor_execute", record)

    assert primed == again == ["Chest pain"]
    assert _library_queries(statements) == []


async def test_publishing_and_approving_a_station_shows_it_on_the_next_read(
    client: AsyncClient, make_actor, db_session: AsyncSession, redis_cache: None
) -> None:  # type: ignore[no-untyped-def]
    token = await a_browser(db_session, make_actor, "reader@example.com")
    await a_library_station(db_session, "Chest pain")
    draft_id = await a_library_station(db_session, "Headache", published=False)
    assert await _titles(client, token) == ["Chest pain"]

    user = (await db_session.execute(select(User).where(User.email == "reader@example.com"))).scalar_one()
    await service_versions.publish_version(
        db_session, None, draft_id, 1, actor_id=user.id, now=datetime.now(UTC)
    )
    await stations_service.set_station_approved(db_session, None, draft_id, approved=True)
    # The request would have committed; the queued bumps run once it has.
    await cache.flush_cache_ops(db_session)

    assert sorted(await _titles(client, token)) == ["Chest pain", "Headache"]

    await stations_service.set_station_approved(db_session, None, draft_id, approved=False)
    await cache.flush_cache_ops(db_session)

    assert await _titles(client, token) == ["Chest pain"]


async def test_an_organisations_own_station_bumps_nothing(db_session: AsyncSession) -> None:
    station = Station(owner_kind="org", org_id=uuid.uuid4(), exam_id=uuid.uuid4(), title="Own")
    stations_service.bump_library(db_session, station)

    assert db_session.info.get(cache.PENDING_KEY) is None


async def test_the_first_station_order_is_cached_and_cut_after_the_cache(
    db_session: AsyncSession, redis_cache: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    exam_id = uuid.uuid4()
    ids = [uuid.uuid4() for _ in range(4)]
    calls = 0

    async def fake_first(session, *, exam_id, limit, exclude_ids=()):  # type: ignore[no-untyped-def]
        nonlocal calls
        calls += 1
        return ids

    monkeypatch.setattr(repository_library, "first_station_ids", fake_first)
    first = await service_plan_window._first_station_ids(  # noqa: SLF001
        db_session, exam_id=exam_id, limit=2, exclude_ids={ids[0]}
    )
    second = await service_plan_window._first_station_ids(  # noqa: SLF001
        db_session, exam_id=exam_id, limit=3, exclude_ids=set()
    )

    assert first == [ids[1], ids[2]]
    assert second == ids[:3]
    assert calls == 1


async def test_the_catalog_reads_are_cached_until_a_write_commits(
    db_session: AsyncSession, redis_cache: None
) -> None:
    await ensure_exam(db_session, "sca")
    before = await catalog.exam_codes(db_session)
    await ensure_exam(db_session, "ortho")
    assert await catalog.exam_codes(db_session) == before

    catalog.bump_catalog(db_session)
    await cache.flush_cache_ops(db_session)

    assert "ortho" in await catalog.exam_codes(db_session)


async def test_with_redis_off_every_read_is_fresh_and_the_same(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    token = await a_browser(db_session, make_actor, "off@example.com")
    await a_library_station(db_session, "Chest pain")
    assert await _titles(client, token) == ["Chest pain"]

    await a_library_station(db_session, "Headache")

    # No cache, so nothing needs bumping for the new station to show.
    assert sorted(await _titles(client, token)) == ["Chest pain", "Headache"]
    assert await catalog.exam_codes(db_session) == await catalog.exam_codes(db_session)


async def test_archiving_a_station_removes_it_from_the_next_read(
    client: AsyncClient, make_actor, db_session: AsyncSession, redis_cache: None
) -> None:  # type: ignore[no-untyped-def]
    token = await a_browser(db_session, make_actor, "archiver@example.com")
    station_id = await a_library_station(db_session, "Chest pain")
    assert await _titles(client, token) == ["Chest pain"]
    user = (await db_session.execute(select(User).where(User.email == "archiver@example.com"))).scalar_one()
    actor = Principal(user_id=user.id, email=user.email, is_platform_admin=True)

    await service_versions.archive_version(
        db_session, None, station_id, 1, now=datetime.now(UTC), actor=actor
    )
    await cache.flush_cache_ops(db_session)

    assert await _titles(client, token) == []


async def test_a_programme_write_refreshes_the_cached_organisation_exams(
    db_session: AsyncSession, redis_cache: None
) -> None:
    from app.features.catalog import service_programmes
    from app.features.tenancy.models import Organization

    org = Organization(slug=f"cached-{uuid.uuid4().hex[:8]}", name="Cached", org_type="institution")
    db_session.add(org)
    await db_session.flush()
    await ensure_exam(db_session, "sca")
    assert await catalog.org_exam_ids(db_session, org.id) == []

    await service_programmes.add_programme(db_session, org.id, exam_code="sca")
    await cache.flush_cache_ops(db_session)

    assert len(await catalog.org_exam_ids(db_session, org.id)) == 1
