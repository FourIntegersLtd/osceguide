import pytest
from httpx import AsyncClient

from app.core.settings import get_settings

pytestmark = pytest.mark.db


async def test_health_reports_database_ok(client: AsyncClient) -> None:
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["checks"] == {"database": "ok", "redis": "disabled"}
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
