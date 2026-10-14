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


async def test_joining_before_the_window_opens_is_too_early_to_join(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Distinct from `peer_session_not_open`: the session is fine, it just is not time yet."""
    owner = await make_actor("early-owner@example.com")
    taker = await make_actor("early-taker@example.com")
    starts_later = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    offered = await client.post(
        "/api/v1/marketplace/slots",
        json={"exam_code": "sca", "starts_at": starts_later},
        headers=bearer(owner),
    )
    assert offered.status_code == 201, offered.text
    claimed = await client.post(
        f"/api/v1/marketplace/slots/{offered.json()['id']}/claim", headers=bearer(taker)
    )
    assert claimed.status_code == 201, claimed.text

    too_early = await client.post(
        f"/api/v1/me/peer-sessions/{claimed.json()['id']}/join", headers=bearer(taker)
    )
    assert too_early.status_code == 409
    assert too_early.json()["code"] == "too_early_to_join"


async def test_claiming_an_already_claimed_slot_names_the_race(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The second claimer is told someone beat them to it, not just that it is gone."""
    owner = await make_actor("race-owner@example.com")
    first = await make_actor("race-first@example.com")
    second = await make_actor("race-second@example.com")
    starts_soon = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
    offered = await client.post(
        "/api/v1/marketplace/slots",
        json={"exam_code": "sca", "starts_at": starts_soon},
        headers=bearer(owner),
    )
    assert offered.status_code == 201, offered.text
    post_id = offered.json()["id"]
    assert (
        await client.post(f"/api/v1/marketplace/slots/{post_id}/claim", headers=bearer(first))
    ).status_code == 201

    beaten = await client.post(f"/api/v1/marketplace/slots/{post_id}/claim", headers=bearer(second))
    assert beaten.status_code == 409
    assert beaten.json()["code"] == "slot_already_claimed"


async def test_cancelling_a_joined_session_ends_its_live_consultation(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """A booking cancelled after both sides joined must not leave the room running
    underneath it — the other person could otherwise still be sitting in it."""
    owner = await make_actor("cancel-live-owner@example.com")
    taker = await make_actor("cancel-live-taker@example.com")
    post, as_taker = await offer_and_claim(client, owner, taker)
    join_url = f"/api/v1/me/peer-sessions/{as_taker['id']}/join"
    assert (await client.post(join_url, headers=bearer(taker))).status_code == 200
    joined = await client.post(join_url, headers=bearer(owner))
    assert joined.status_code == 200, joined.text
    practice_session_id = joined.json()["practice_session_id"]
    assert practice_session_id is not None

    cancelled = await client.post(f"/api/v1/me/peer-sessions/{as_taker['id']}/cancel", headers=bearer(owner))
    assert cancelled.status_code == 204, cancelled.text

    live_session = await client.get(
        f"/api/v1/me/practice-sessions/{practice_session_id}", headers=bearer(taker)
    )
    assert live_session.status_code == 200, live_session.text
    assert (live_session.json()["status"], live_session.json()["end_reason"]) == ("ended", "cancelled")


async def test_listing_slots_filters_by_status(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """`status` narrows the feed to one of the two rows it already carries."""
    owner = await make_actor("status-filter-owner@example.com")
    taker = await make_actor("status-filter-taker@example.com")
    starts_soon = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
    available = (
        await client.post(
            "/api/v1/marketplace/slots",
            json={"exam_code": "sca", "starts_at": starts_soon},
            headers=bearer(owner),
        )
    ).json()
    claimed, _ = await offer_and_claim(client, owner, taker)

    only_available = await client.get(
        "/api/v1/marketplace/slots", params={"status": "available"}, headers=bearer(taker)
    )
    assert only_available.status_code == 200, only_available.text
    assert [row["id"] for row in only_available.json()["items"]] == [available["id"]]

    only_claimed = await client.get(
        "/api/v1/marketplace/slots", params={"status": "claimed"}, headers=bearer(taker)
    )
    assert only_claimed.status_code == 200, only_claimed.text
    assert [row["id"] for row in only_claimed.json()["items"]] == [claimed["id"]]


async def test_listing_slots_filters_by_when(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """`when`, read against the server's own clock, splits future slots from ones
    already started — the same split `SlotSections.tsx` made client-side."""
    owner = await make_actor("when-filter-owner@example.com")
    future = (
        await client.post(
            "/api/v1/marketplace/slots",
            json={"exam_code": "sca", "starts_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat()},
            headers=bearer(owner),
        )
    ).json()
    past = (
        await client.post(
            "/api/v1/marketplace/slots",
            json={"exam_code": "sca", "starts_at": (datetime.now(UTC) - timedelta(hours=1)).isoformat()},
            headers=bearer(owner),
        )
    ).json()

    upcoming = await client.get(
        "/api/v1/marketplace/slots", params={"when": "upcoming"}, headers=bearer(owner)
    )
    assert upcoming.status_code == 200, upcoming.text
    assert [row["id"] for row in upcoming.json()["items"]] == [future["id"]]

    gone_by = await client.get("/api/v1/marketplace/slots", params={"when": "past"}, headers=bearer(owner))
    assert gone_by.status_code == 200, gone_by.text
    assert [row["id"] for row in gone_by.json()["items"]] == [past["id"]]


async def test_listing_my_sessions_filters_by_when(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """`when=upcoming` keeps a session still within its join window; a cancelled
    one moves to `when=past` regardless of its start time — the same rule
    `isUpcoming` in `UpcomingSessions.tsx` applied client-side."""
    owner = await make_actor("session-when-owner@example.com")
    taker = await make_actor("session-when-taker@example.com")
    live, as_taker = await offer_and_claim(client, owner, taker)
    cancel_post, cancel_as_taker = await offer_and_claim(client, owner, taker)
    cancelled = await client.post(
        f"/api/v1/me/peer-sessions/{cancel_as_taker['id']}/cancel", headers=bearer(taker)
    )
    assert cancelled.status_code == 204, cancelled.text

    upcoming = await client.get(
        "/api/v1/me/peer-sessions", params={"when": "upcoming"}, headers=bearer(taker)
    )
    assert upcoming.status_code == 200, upcoming.text
    assert [row["id"] for row in upcoming.json()["items"]] == [as_taker["id"]]

    past = await client.get("/api/v1/me/peer-sessions", params={"when": "past"}, headers=bearer(taker))
    assert past.status_code == 200, past.text
    assert [row["id"] for row in past.json()["items"]] == [cancel_as_taker["id"]]


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


async def test_my_posts_reports_a_withdrawn_slot_as_cancelled(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    owner = await make_actor("cancelled-owner@example.com")
    taker = await make_actor("cancelled-taker@example.com")
    post, _ = await offer_and_claim(client, owner, taker)
    post_id = post["id"]

    withdrawn = await client.delete(f"/api/v1/marketplace/slots/{post_id}", headers=bearer(owner))
    assert withdrawn.status_code == 204, withdrawn.text

    mine = (await client.get("/api/v1/me/marketplace/posts", headers=bearer(owner))).json()["items"]
    assert [(row["id"], row["status"]) for row in mine] == [(post_id, "cancelled")]
