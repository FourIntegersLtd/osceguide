import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from tests.support.library import add_unbound_station, bind_to_template, publish_library_station
from tests.support.sittings import org_by_slug, org_with_admin

pytestmark = pytest.mark.db


async def test_health_reports_database_ok(client: AsyncClient) -> None:
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["checks"] == {"database": "ok", "redis": "disabled", "content": "ok"}
    assert r.headers["X-Request-ID"]


async def test_health_reports_the_commit_railway_built(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Railway sets RAILWAY_GIT_COMMIT_SHA; the promote workflow reads it back from `/health`."""
    monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", "67aeddd0f1c2b3a4d5e6f708192a3b4c5d6e7f80")
    get_settings.cache_clear()
    try:
        health_response = await client.get("/health")
    finally:
        monkeypatch.delenv("RAILWAY_GIT_COMMIT_SHA")
        get_settings.cache_clear()
    assert health_response.json()["commit"] == "67aeddd0f1c2b3a4d5e6f708192a3b4c5d6e7f80"


async def test_health_is_degraded_when_a_published_station_has_no_template(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Production once served 449 stations with no written brief while `/health` said ok."""
    await publish_library_station(db_session)
    body = (await client.get("/health")).json()
    assert body["status"] == "degraded"
    assert body["checks"] == {"database": "ok", "redis": "disabled", "content": "error"}


async def test_health_content_is_ok_once_the_station_is_bound(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await bind_to_template(db_session, await publish_library_station(db_session))
    body = (await client.get("/health")).json()
    assert body["status"] == "ok"
    assert body["checks"] == {"database": "ok", "redis": "disabled", "content": "ok"}


async def test_health_content_ignores_draft_and_org_stations(
    client: AsyncClient,
    db_session: AsyncSession,
    make_actor,  # type: ignore[no-untyped-def]
) -> None:
    await org_with_admin(client, make_actor, "health-org")
    org = await org_by_slug(db_session, "health-org")
    await add_unbound_station(db_session, "sca", org_id=None, status="draft")
    await add_unbound_station(db_session, "sca", org_id=org.id, status="published")
    body = (await client.get("/health")).json()
    assert body["status"] == "ok"
    assert body["checks"] == {"database": "ok", "redis": "disabled", "content": "ok"}
