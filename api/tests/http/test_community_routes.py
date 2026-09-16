"""Posting, liking and removing — with the authorisation b2c lacks."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def ask(client: AsyncClient, token: str, title: str = "How?") -> dict:
    response = await client.post(
        "/api/v1/community/questions",
        json={"title": title, "body": "I am stuck on chest pain stations."},
        headers=bearer(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_a_question_is_asked_and_listed(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("c1@example.com")
    await ask(client, token)
    listed = await client.get("/api/v1/community/questions", headers=bearer(token))
    assert [q["title"] for q in listed.json()["items"]] == ["How?"]
    assert listed.json()["items"][0]["reply_count"] == 0


async def test_empty_content_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("c2@example.com")
    response = await client.post(
        "/api/v1/community/questions",
        json={"title": "T", "body": "   "},
        headers=bearer(token),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "empty_content"


async def test_a_reply_is_counted_on_its_question(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    author = await make_actor("c3@example.com")
    question = await ask(client, author)
    responder = await make_actor("c3-b@example.com")

    reply = await client.post(
        f"/api/v1/community/questions/{question['id']}/replies",
        json={"body": "Start with the history."},
        headers=bearer(responder),
    )
    assert reply.status_code == 201
    assert reply.json()["parent_id"] == question["id"]

    listed = await client.get("/api/v1/community/questions", headers=bearer(author))
    assert listed.json()["items"][0]["reply_count"] == 1


async def test_liking_twice_counts_once(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """b2c increments a counter, so a double tap counts twice and cannot be
    undone."""
    token = await make_actor("c4@example.com")
    question = await ask(client, token)
    url = f"/api/v1/community/posts/{question['id']}/like"

    first = await client.post(url, headers=bearer(token))
    second = await client.post(url, headers=bearer(token))
    assert first.json()["like_count"] == 1
    assert second.json()["like_count"] == 1
    assert second.json()["liked_by_me"] is True


async def test_a_like_can_be_undone(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("c5@example.com")
    question = await ask(client, token)
    url = f"/api/v1/community/posts/{question['id']}/like"
    await client.post(url, headers=bearer(token))
    removed = await client.delete(url, headers=bearer(token))
    assert removed.json()["like_count"] == 0
    assert removed.json()["liked_by_me"] is False


async def test_an_author_may_remove_their_own_post(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("c6@example.com")
    question = await ask(client, token)
    removed = await client.delete(
        f"/api/v1/community/posts/{question['id']}", headers=bearer(token)
    )
    assert removed.status_code == 204

    listed = await client.get("/api/v1/community/questions", headers=bearer(token))
    assert listed.json()["items"] == []


async def test_someone_else_may_not_remove_it(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The rule b2c's routes do not have at all."""
    author = await make_actor("c7@example.com")
    question = await ask(client, author)
    stranger = await make_actor("c7-b@example.com")

    response = await client.delete(
        f"/api/v1/community/posts/{question['id']}", headers=bearer(stranger)
    )
    assert response.status_code == 403
    assert response.json()["code"] == "post_not_yours"


async def test_a_platform_admin_may_remove_anything(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    author = await make_actor("c8@example.com")
    question = await ask(client, author)
    admin = await make_actor("c8-admin@osceguide.com", platform_admin=True)

    response = await client.delete(
        f"/api/v1/community/posts/{question['id']}", headers=bearer(admin)
    )
    assert response.status_code == 204


async def test_community_needs_a_token(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/community/questions")).status_code == 401
