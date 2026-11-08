"""The console says a station is marked by the same rule the sitting results use, and counts its drafts."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts.models import Attempt
from app.features.catalog.models import Exam
from app.features.sittings.models import Slot
from tests.http.test_reviews_routes import a_slot, a_supervisor, org_with_admin
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def _console_slot(
    client: AsyncClient, admin: str, db_session: AsyncSession, slot_id: uuid.UUID
) -> dict:  # type: ignore[type-arg]
    circuit_id = (await db_session.execute(select(Slot.circuit_id).where(Slot.id == slot_id))).scalar_one()
    response = await client.get(f"/api/v1/orgs/kings/circuits/{circuit_id}/console", headers=bearer(admin))
    assert response.status_code == 200, response.text
    return response.json()["slots"][0]


async def test_an_automatically_marked_station_is_marked_though_nobody_reviewed_it(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    slot_id = await a_slot(db_session, org_id)
    before = await _console_slot(client, admin, db_session, slot_id)
    exam_id = await db_session.scalar(select(Exam.id).where(Exam.code == "sca"))
    trainee_id = (await db_session.execute(select(Slot.trainee_id).where(Slot.id == slot_id))).scalar_one()
    db_session.add(
        Attempt(
            kind="exam_slot",
            user_id=trainee_id,
            org_id=org_id,
            exam_id=exam_id,
            slot_id=slot_id,
            status="evaluated",
        )
    )
    await db_session.commit()

    after = await _console_slot(client, admin, db_session, slot_id)

    assert (before["marked"], before["has_review"], before["draft_reviews"]) == (False, False, 0)
    assert (after["marked"], after["has_review"], after["draft_reviews"]) == (True, False, 0)
    assert (before["ai_marked"], after["ai_marked"]) == (False, True)


async def test_drafts_are_counted_and_do_not_make_a_station_marked(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    supervisor_id, second = await a_supervisor(db_session, org_id, "observer@example.com")
    slot_id = await a_slot(db_session, org_id, supervisor=supervisor_id)
    url = f"/api/v1/orgs/kings/slots/{slot_id}/reviews/mine"
    draft = {"field_values": {"communication.score": "G"}, "status": "draft"}
    await client.put(url, json=draft, headers=bearer(admin))
    await client.put(url, json=draft, headers=bearer(second))

    slot = await _console_slot(client, admin, db_session, slot_id)

    assert (slot["marked"], slot["has_review"], slot["draft_reviews"]) == (False, True, 2)
    assert slot["ai_marked"] is False, "a person's draft is not the engine's mark"


async def test_a_completed_review_makes_the_station_marked_and_leaves_no_draft(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    slot_id = await a_slot(db_session, org_id)
    await client.put(
        f"/api/v1/orgs/kings/slots/{slot_id}/reviews/mine",
        json={"field_values": {"communication.score": "G"}, "status": "completed"},
        headers=bearer(admin),
    )

    slot = await _console_slot(client, admin, db_session, slot_id)

    assert (slot["marked"], slot["has_review"], slot["draft_reviews"]) == (True, True, 0)
    assert slot["ai_marked"] is False
