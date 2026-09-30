"""The landing page's numbers, and the forms anybody may post to."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.support.tokens import bearer

pytestmark = pytest.mark.db

STATS = "/api/v1/site/statistics"
MESSAGES = "/api/v1/site/messages"


async def test_the_landing_numbers_are_readable_without_signing_in(client: AsyncClient) -> None:
    """The band hid itself because asking 404'd on every view of the busiest page."""
    read = await client.get(STATS)
    assert read.status_code == 200, read.text
    body = read.json()
    for field in ("consultations", "feedback", "debriefs", "users", "stations"):
        assert isinstance(body[field], int)
    # Said rather than implied: these are counted, not live.
    assert body["as_of"]


async def test_a_visitor_can_write_to_us_without_an_account(client: AsyncClient) -> None:
    sent = await client.post(
        MESSAGES,
        json={"kind": "contact", "name": "Amara", "email": "amara@example.com", "body": "How do I book?"},
    )
    assert sent.status_code == 201, sent.text
    assert sent.json()["kind"] == "contact"
    # An id and nothing else: support can be quoted one.
    assert set(sent.json()) == {"id", "kind"}


async def test_feedback_may_be_anonymous_and_contact_may_not(client: AsyncClient) -> None:
    anonymous = await client.post(
        MESSAGES, json={"kind": "product_feedback", "body": "The timer is hard to read."}
    )
    assert anonymous.status_code == 201, anonymous.text

    unanswerable = await client.post(MESSAGES, json={"kind": "contact", "body": "Call me."})
    assert unanswerable.status_code == 422, unanswerable.text
    assert unanswerable.json()["code"] == "invalid_message"


async def test_a_signed_in_sender_is_filed_against_their_account(
    client: AsyncClient,
    make_actor,  # type: ignore[no-untyped-def]
) -> None:
    token = await make_actor("amara@example.com")
    sent = await client.post(
        MESSAGES,
        json={"kind": "product_feedback", "body": "The station list is slow.", "source": "/app/me/stations"},
        headers=bearer(token),
    )
    assert sent.status_code == 201, sent.text

    root = await make_actor("root@osceguide.com", platform_admin=True)
    inbox = await client.get(
        "/api/v1/platform/site/messages", params={"kind": "product_feedback"}, headers=bearer(root)
    )
    assert inbox.status_code == 200, inbox.text
    mine = next(m for m in inbox.json()["items"] if m["body"] == "The station list is slow.")
    assert mine["user_id"] is not None
    assert mine["source"] == "/app/me/stations"


async def test_the_inbox_is_not_everybody_s_to_read(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    ordinary = await make_actor("someone@example.com")
    assert (await client.get("/api/v1/platform/site/messages", headers=bearer(ordinary))).status_code == 403
    assert (await client.get("/api/v1/platform/site/messages")).status_code == 401


async def test_a_message_can_be_taken_out_of_the_queue(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    sent = await client.post(
        MESSAGES,
        json={"kind": "contact", "email": "amara@example.com", "body": "Is there a student rate?"},
    )
    message_id = sent.json()["id"]

    root = await make_actor("root@osceguide.com", platform_admin=True)
    handled = await client.post(f"/api/v1/platform/site/messages/{message_id}/handled", headers=bearer(root))
    assert handled.status_code == 200, handled.text
    assert handled.json()["handled_at"] is not None


async def test_the_inbox_filters_on_handled_and_pages(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The console's queue is the unhandled rows; the archive is the rest. Both come from SQL."""
    for body in ("First question", "Second question"):
        sent = await client.post(
            MESSAGES, json={"kind": "contact", "name": "Amara", "email": "amara@example.com", "body": body}
        )
        assert sent.status_code == 201, sent.text
    root = await make_actor("root@osceguide.com", platform_admin=True)
    everything = await client.get("/api/v1/platform/site/messages", headers=bearer(root))
    first = next(m for m in everything.json()["items"] if m["body"] == "First question")
    handled = await client.post(f"/api/v1/platform/site/messages/{first['id']}/handled", headers=bearer(root))
    assert handled.status_code == 200, handled.text

    queue = await client.get(
        "/api/v1/platform/site/messages", params={"handled": "false"}, headers=bearer(root)
    )
    archive = await client.get(
        "/api/v1/platform/site/messages", params={"handled": "true"}, headers=bearer(root)
    )
    assert [m["body"] for m in queue.json()["items"]] == ["Second question"]
    assert [m["body"] for m in archive.json()["items"]] == ["First question"]

    one = await client.get("/api/v1/platform/site/messages", params={"limit": 1}, headers=bearer(root))
    assert len(one.json()["items"]) == 1
    rest = await client.get(
        "/api/v1/platform/site/messages",
        params={"limit": 1, "cursor": one.json()["next_cursor"]},
        headers=bearer(root),
    )
    assert len(rest.json()["items"]) == 1
    assert rest.json()["items"][0]["id"] != one.json()["items"][0]["id"]
