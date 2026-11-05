"""The slot's review list names who finished a review, rates it, and says whether they agree.

Only the supervisor named on the circuit and an administrator may review a slot, so a slot has at
most those two reviewers.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.http.test_reviews_routes import a_slot, a_supervisor, org_with_admin
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def _put(client: AsyncClient, token: str, slot_id, rating: str, status: str) -> None:  # type: ignore[no-untyped-def]
    response = await client.put(
        f"/api/v1/orgs/kings/slots/{slot_id}/reviews/mine",
        json={"field_values": {"communication.score": rating}, "status": status},
        headers=bearer(token),
    )
    assert response.status_code == 200, response.text


async def _reviews(client: AsyncClient, token: str, slot_id) -> dict:  # type: ignore[no-untyped-def,type-arg]
    response = await client.get(f"/api/v1/orgs/kings/slots/{slot_id}/reviews", headers=bearer(token))
    assert response.status_code == 200, response.text
    return response.json()


async def test_a_finished_review_carries_its_reviewers_name_and_rating_and_a_draft_stays_anonymous(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    supervisor_id, supervisor = await a_supervisor(db_session, org_id, "patel@example.com")
    slot_id = await a_slot(db_session, org_id, supervisor=supervisor_id)
    await _put(client, supervisor, slot_id, "G", "completed")
    await _put(client, admin, slot_id, "R", "draft")

    body = await _reviews(client, supervisor, slot_id)

    shown = sorted((item["status"], item["reviewer_name"], item["overall"]) for item in body["items"])
    assert shown == [("completed", "patel@example.com", "G"), ("draft", None, None)]
    assert body["reviewers_agree"] is None


async def test_two_finished_reviews_that_match_agree(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    supervisor_id, supervisor = await a_supervisor(db_session, org_id, "patel@example.com")
    slot_id = await a_slot(db_session, org_id, supervisor=supervisor_id)
    await _put(client, supervisor, slot_id, "G", "completed")
    await _put(client, admin, slot_id, "G", "completed")

    assert (await _reviews(client, admin, slot_id))["reviewers_agree"] is True


async def test_two_finished_reviews_that_differ_do_not_agree(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    supervisor_id, supervisor = await a_supervisor(db_session, org_id, "patel@example.com")
    slot_id = await a_slot(db_session, org_id, supervisor=supervisor_id)
    await _put(client, supervisor, slot_id, "G", "completed")
    await _put(client, admin, slot_id, "R", "completed")

    assert (await _reviews(client, admin, slot_id))["reviewers_agree"] is False
