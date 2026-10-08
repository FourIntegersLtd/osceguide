"""A person's inbox, and staff writing to it. Failing requests go last: a refused request rolls
back the shared test session."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.support.tokens import bearer

pytestmark = pytest.mark.db

ME = "/api/v1/me/messages"


async def my_id(client: AsyncClient, token: str) -> str:
    return (await client.get("/api/v1/me", headers=bearer(token))).json()["id"]


async def test_a_note_reaches_the_recipient_and_is_audited(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor(f"root-{uuid.uuid4().hex[:6]}@osceguide.com", platform_admin=True)
    reader = await make_actor("reader@example.com")
    reader_id = await my_id(client, reader)

    sent = await client.post(
        f"/api/v1/platform/users/{reader_id}/messages",
        json={"subject": "Your trial", "body": "We extended it."},
        headers=bearer(root),
    )
    assert sent.status_code == 201, sent.text
    assert sent.json()["kind"] == "note"

    count = await client.get(f"{ME}/unread-count", headers=bearer(reader))
    assert count.json() == {"count": 1}
    listed = (await client.get(ME, headers=bearer(reader))).json()["items"]
    assert [(m["subject"], m["body"], m["from_label"], m["read"]) for m in listed] == [
        ("Your trial", "We extended it.", "OSCE Guide team", False)
    ]

    marked = await client.post(f"{ME}/{listed[0]['id']}/read", headers=bearer(reader))
    assert marked.status_code == 204
    assert (await client.get(f"{ME}/unread-count", headers=bearer(reader))).json() == {"count": 0}
    assert (await client.get(ME, headers=bearer(reader))).json()["items"][0]["read"] is True

    history = await client.get(f"/api/v1/platform/users/{reader_id}/audit", headers=bearer(root))
    assert [row["action"] for row in history.json()["items"]] == ["inbox.note_sent"]


async def test_read_all_clears_the_count(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor(f"root-{uuid.uuid4().hex[:6]}@osceguide.com", platform_admin=True)
    reader = await make_actor("reader@example.com")
    reader_id = await my_id(client, reader)
    for subject in ("One", "Two"):
        await client.post(
            f"/api/v1/platform/users/{reader_id}/messages",
            json={"subject": subject, "body": "x"},
            headers=bearer(root),
        )
    assert (await client.get(f"{ME}/unread-count", headers=bearer(reader))).json() == {"count": 2}
    assert (await client.post(f"{ME}/read-all", headers=bearer(reader))).status_code == 204
    assert (await client.get(f"{ME}/unread-count", headers=bearer(reader))).json() == {"count": 0}


async def test_an_announcement_reaches_existing_accounts_not_later_ones_and_can_be_withdrawn(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor(f"root-{uuid.uuid4().hex[:6]}@osceguide.com", platform_admin=True)
    early = await make_actor("early@example.com")
    late = await make_actor("late@example.com")
    # Everything in a test shares one transaction timestamp, so say who joined later.
    await db_session.execute(
        text("UPDATE users SET created_at = now() - interval '1 day' WHERE email = 'early@example.com'")
    )
    await db_session.execute(
        text("UPDATE users SET created_at = now() + interval '1 day' WHERE email = 'late@example.com'")
    )

    posted = await client.post(
        "/api/v1/platform/announcements",
        json={"subject": "New stations", "body": "Fifty new cases."},
        headers=bearer(root),
    )
    assert posted.status_code == 201, posted.text
    announcement_id = posted.json()["id"]

    assert (await client.get(f"{ME}/unread-count", headers=bearer(early))).json() == {"count": 1}
    assert (await client.get(f"{ME}/unread-count", headers=bearer(late))).json() == {"count": 0}
    await client.post(f"{ME}/{announcement_id}/read", headers=bearer(early))

    staff = await client.get("/api/v1/platform/announcements", headers=bearer(root))
    assert [(a["subject"], a["read_count"], a["withdrawn_at"]) for a in staff.json()["items"]] == [
        ("New stations", 1, None)
    ]

    withdrawn = await client.post(
        f"/api/v1/platform/announcements/{announcement_id}/withdraw", headers=bearer(root)
    )
    assert withdrawn.status_code == 200, withdrawn.text
    assert withdrawn.json()["withdrawn_at"] is not None
    assert (await client.get(ME, headers=bearer(early))).json()["items"] == []
    assert (await client.get(f"{ME}/unread-count", headers=bearer(early))).json() == {"count": 0}


async def test_refusals(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor(f"root-{uuid.uuid4().hex[:6]}@osceguide.com", platform_admin=True)
    reader = await make_actor("reader@example.com")
    other = await make_actor("other@example.com")
    reader_id = await my_id(client, reader)
    await client.post(
        f"/api/v1/platform/users/{reader_id}/messages",
        json={"subject": "Private", "body": "x"},
        headers=bearer(root),
    )
    message_id = (await client.get(ME, headers=bearer(reader))).json()["items"][0]["id"]

    # Somebody else's message does not exist as far as they can tell.
    theirs = await client.post(f"{ME}/{message_id}/read", headers=bearer(other))
    assert theirs.status_code == 404
    assert theirs.json()["code"] == "inbox_message_not_found"

    not_staff = await client.post(
        f"/api/v1/platform/users/{reader_id}/messages",
        json={"subject": "Hi", "body": "x"},
        headers=bearer(other),
    )
    assert not_staff.status_code == 403
    nobody = await client.post(
        f"/api/v1/platform/users/{uuid.uuid4()}/messages",
        json={"subject": "Hi", "body": "x"},
        headers=bearer(root),
    )
    assert nobody.status_code == 404
    assert (await client.get(ME)).status_code == 401
