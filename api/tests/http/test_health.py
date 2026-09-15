import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.db


async def test_health_reports_database_ok(client: AsyncClient) -> None:
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["checks"] == {"database": "ok", "redis": "disabled"}
    assert r.headers["X-Request-ID"]
