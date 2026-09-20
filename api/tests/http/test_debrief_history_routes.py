"""Full debrief history stays private and does not stop at the memory window."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.tutor_memory import repository
from tests.http.test_attempt_material_routes import _entitled_attempt
from tests.support.finished_consultation import finish_consultation
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def test_debrief_history_pages_and_links_the_source_consultation(
    client: AsyncClient,
    db_session: AsyncSession,
    make_actor,
) -> None:
    token = await make_actor("debrief-history-owner@example.com")
    other = await make_actor("debrief-history-other@example.com")
    sat = await _entitled_attempt(db_session, "debrief-history-owner@example.com")
    await finish_consultation(db_session, sat.attempt_id)
    await db_session.commit()
    summary_ids = set()
    for _ in range(3):
        started = await client.post(
            f"/api/v1/attempts/{sat.attempt_id}/debriefs",
            headers=bearer(token),
        )
        assert started.status_code == 201, started.text
        summary = await repository.add_debrief_summary(
            db_session,
            attempt_id=uuid.UUID(started.json()["id"]),
            user_id=sat.user_id,
            exam_id=None,
            key_insights=["Ask about concerns"],
            action_plan=[],
            narrative="Practise exploring ICE.",
            model_used=None,
        )
        summary_ids.add(str(summary.id))
        await db_session.commit()

    first = await client.get("/api/v1/me/debriefs?limit=2", headers=bearer(token))
    assert first.status_code == 200, first.text
    assert len(first.json()["items"]) == 2
    second = await client.get(
        "/api/v1/me/debriefs",
        headers=bearer(token),
        params={"limit": 2, "cursor": first.json()["next_cursor"]},
    )
    assert second.status_code == 200, second.text
    assert second.json()["next_cursor"] is None
    items = first.json()["items"] + second.json()["items"]
    assert {item["id"] for item in items} == summary_ids
    assert all(item["source_attempt_id"] == str(sat.attempt_id) for item in items)
    private = await client.get("/api/v1/me/debriefs", headers=bearer(other))
    assert private.json()["items"] == []
    assert (await client.get("/api/v1/me/debriefs")).status_code == 401
