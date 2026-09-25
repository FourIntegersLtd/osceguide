"""Offering, claiming, joining and cancelling a peer practice slot over HTTP."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.support.catalog import ensure_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


@pytest.fixture(autouse=True)
async def an_exam(db_session: AsyncSession) -> None:
    await ensure_exam(db_session, "sca")


async def offer_and_claim(
    client: AsyncClient, owner: Any, taker: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Offer a slot starting in five minutes and have `taker` claim it."""
    starts_soon = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
    offered = await client.post(
        "/api/v1/marketplace/slots",
        json={"exam_code": "sca", "starts_at": starts_soon},
        headers=bearer(owner),
    )
    assert offered.status_code == 201, offered.text
    claimed = await client.post(
        f"/api/v1/marketplace/slots/{offered.json()['id']}/claim", headers=bearer(taker)
    )
    assert claimed.status_code == 201, claimed.text
    return offered.json(), claimed.json()


async def test_offer_claim_join_and_cancel(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    owner = await make_actor("walk-owner@example.com")
    taker = await make_actor("walk-taker@example.com")
    stranger = await make_actor("walk-stranger@example.com")
    post, as_taker = await offer_and_claim(client, owner, taker)
    assert (post["owner_username"], post["is_mine"], post["status"]) == (
        "walk-owner@example.com",
        True,
        "available",
    )
    assert (as_taker["user_role"], as_taker["partner_username"], as_taker["my_role"]) == (
        "claimer",
        "walk-owner@example.com",
        None,
    )
    assert as_taker["room_name"] == f"peer_{as_taker['id']}"
    assert as_taker["partner_user_id"] == post["owner_user_id"]

    my_posts = (await client.get("/api/v1/me/marketplace/posts", headers=bearer(owner))).json()["items"]
    assert [(mine["status"], mine["claimed_by_username"]) for mine in my_posts] == [
        ("claimed", "walk-taker@example.com")
    ]
    owner_sessions = (await client.get("/api/v1/me/peer-sessions", headers=bearer(owner))).json()["items"]
    assert [(booked["user_role"], booked["partner_username"]) for booked in owner_sessions] == [
        ("poster", "walk-taker@example.com")
    ]

    join_url = f"/api/v1/me/peer-sessions/{as_taker['id']}/join"
    assert (await client.post(join_url, headers=bearer(stranger))).status_code == 404

    joined = await client.post(join_url, headers=bearer(taker))
    assert joined.status_code == 200, joined.text
    taker_view = joined.json()
    assert taker_view["status"] == "active"
    owner_view = (await client.post(join_url, headers=bearer(owner))).json()
    assert owner_view["practice_session_id"] == taker_view["practice_session_id"] is not None
    assert {owner_view["my_role"], taker_view["my_role"]} == {"doctor", "patient"}

    cancel_url = f"/api/v1/me/peer-sessions/{as_taker['id']}/cancel"
    assert (await client.post(cancel_url, headers=bearer(owner))).status_code == 204
    cancelled_again = await client.post(cancel_url, headers=bearer(owner))
    assert (cancelled_again.status_code, cancelled_again.json()["code"]) == (409, "peer_session_not_open")

    # A cancelled session must stay shut, even inside its join window.
    rejoined = await client.post(join_url, headers=bearer(taker))
    assert (rejoined.status_code, rejoined.json()["code"]) == (409, "peer_session_not_open")


async def test_withdrawing_a_claimed_slot_cancels_its_session(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    owner = await make_actor("withdraw-owner@example.com")
    taker = await make_actor("withdraw-taker@example.com")
    post, as_taker = await offer_and_claim(client, owner, taker)

    withdrawn = await client.delete(f"/api/v1/marketplace/slots/{post['id']}", headers=bearer(owner))
    assert withdrawn.status_code == 204, withdrawn.text

    taker_sessions = (await client.get("/api/v1/me/peer-sessions", headers=bearer(taker))).json()["items"]
    assert [(booked["id"], booked["status"]) for booked in taker_sessions] == [(as_taker["id"], "cancelled")]
    joined = await client.post(f"/api/v1/me/peer-sessions/{as_taker['id']}/join", headers=bearer(taker))
    assert (joined.status_code, joined.json()["code"]) == (409, "peer_session_not_open")
