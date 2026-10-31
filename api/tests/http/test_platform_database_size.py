"""The staff health route reports the database's size live, and never falls over when it cannot."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.features.health import repository_size
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

HEALTH = "/api/v1/platform/health"
MB = 1024 * 1024


async def test_the_staff_health_report_carries_the_database_size_without_a_worker(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    root = await make_actor("size-root@osceguide.com", platform_admin=True)
    assert (await db_session.execute(text("SELECT count(*) FROM database_size_readings"))).scalar_one() == 0

    body = (await client.get(HEALTH, headers=bearer(root))).json()

    size = body["database_size"]
    assert size["total_bytes"] > 0
    assert size["budget_bytes"] == get_settings().database_size_budget_mb * MB
    assert size["level"] == "ok"
    assert 1 <= len(size["top_relations"]) <= 10
    assert size["forecast"]["state"] == "insufficient_data"
    assert "not enough history" in size["forecast"]["note"]


async def test_the_screen_shows_the_level_against_the_budget_live(
    client: AsyncClient, make_actor, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = await make_actor("size-level@osceguide.com", platform_admin=True)
    monkeypatch.setattr(get_settings(), "database_size_budget_mb", 1)

    size = (await client.get(HEALTH, headers=bearer(root))).json()["database_size"]
    assert size["level"] == "critical"
    assert size["percent_used"] > 100


async def test_the_forecast_uses_the_stored_history(
    client: AsyncClient, make_actor, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = await make_actor("size-forecast@osceguide.com", platform_admin=True)

    async def now_total(_session: AsyncSession) -> int:
        return 140 * MB

    monkeypatch.setattr(repository_size, "database_bytes", now_total)
    for day in range(20):
        await repository_size.save_reading(
            db_session,
            taken_on=date.today() - timedelta(days=20 - day),
            total_bytes=(100 + 2 * day) * MB,
            relations=[],
            alert_level=0,
        )

    forecast = (await client.get(HEALTH, headers=bearer(root))).json()["database_size"]["forecast"]
    assert forecast["state"] == "growing"
    assert forecast["bytes_per_day"] == 2 * MB


async def test_a_database_that_cannot_be_measured_leaves_the_rest_of_the_report_intact(
    client: AsyncClient, make_actor, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = await make_actor("size-broken@osceguide.com", platform_admin=True)

    async def broken(session: AsyncSession) -> int:
        await session.execute(text("select 1/0"))  # a real database error, which poisons a transaction
        return 0

    monkeypatch.setattr(repository_size, "database_bytes", broken)
    response = await client.get(HEALTH, headers=bearer(root))

    assert response.status_code == 200
    body = response.json()
    assert body["database_size"] is None
    assert body["status"] in ("ok", "degraded")
    assert isinstance(body["jobs_by_status"], dict) and "worker_seen_at" in body
    assert body["checks"]["database"] == "ok"


async def test_only_a_platform_admin_sees_it(client: AsyncClient, make_actor) -> None:
    user = await make_actor("size-plain@example.com")
    assert (await client.get(HEALTH, headers=bearer(user))).status_code == 403
