"""Posting, liking and removing — with the authorisation b2c lacks."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.support.catalog import ensure_exam
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
    removed = await client.delete(f"/api/v1/community/posts/{question['id']}", headers=bearer(token))
    assert removed.status_code == 204

    listed = await client.get("/api/v1/community/questions", headers=bearer(token))
    assert listed.json()["items"] == []


async def test_someone_else_may_not_remove_it(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The rule b2c's routes do not have at all."""
    author = await make_actor("c7@example.com")
    question = await ask(client, author)
    stranger = await make_actor("c7-b@example.com")

    response = await client.delete(f"/api/v1/community/posts/{question['id']}", headers=bearer(stranger))
    assert response.status_code == 403
    assert response.json()["code"] == "post_not_yours"


async def test_a_platform_admin_may_remove_anything(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    author = await make_actor("c8@example.com")
    question = await ask(client, author)
    admin = await make_actor("c8-admin@osceguide.com", platform_admin=True)

    response = await client.delete(f"/api/v1/community/posts/{question['id']}", headers=bearer(admin))
    assert response.status_code == 204


async def test_community_needs_a_token(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/community/questions")).status_code == 401


async def a_library_station(db_session: AsyncSession) -> str:
    from app.features.stations import repository as stations_repo

    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    station = await stations_repo.create_station(db_session, None, exam_id=exam.id, title="Chest pain")
    await db_session.flush()
    return str(station.id)


async def test_a_station_comment_is_posted_and_listed(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    """Two of nine routes, and no test touched them: the check constraint
    refused every comment because a comment has a station and no parent."""
    token = await make_actor("commenter@example.com")
    station_id = await a_library_station(db_session)

    posted = await client.post(
        f"/api/v1/stations/{station_id}/comments",
        json={"body": "The examiner wants ICE before the plan."},
        headers=bearer(token),
    )
    assert posted.status_code == 201, posted.text
    assert posted.json()["kind"] == "comment"
    assert posted.json()["parent_id"] is None

    listed = await client.get(f"/api/v1/stations/{station_id}/comments", headers=bearer(token))
    assert [c["body"] for c in listed.json()["items"]] == ["The examiner wants ICE before the plan."]


async def test_an_empty_station_comment_is_refused(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    token = await make_actor("quiet@example.com")
    station_id = await a_library_station(db_session)
    response = await client.post(
        f"/api/v1/stations/{station_id}/comments", json={"body": "  "}, headers=bearer(token)
    )
    assert response.status_code == 422
    assert response.json()["code"] == "empty_content"


async def test_a_comment_on_a_station_that_does_not_exist_is_refused(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor
) -> None:
    """S3: the foreign key used to do this refusal, unmapped, so a client
    naming a station nobody wrote got `internal_error` — a 500 for a typo."""
    token = await make_actor("ghostwriter@example.com")
    response = await client.post(
        f"/api/v1/stations/{uuid.uuid4()}/comments",
        json={"body": "Nobody will read this."},
        headers=bearer(token),
    )
    assert response.status_code == 404
    assert response.json()["code"] == "station_not_found"


# ------------------------------------------------------------------ W1 reads


async def test_a_post_names_its_author(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """`author_name` is joined, not stored.

    The feed used to carry `author_id` and nothing else, so every screen could
    only byline the viewer's own posts and a stranger read as "a colleague".
    `make_actor` names a user by their address, which is what makes the
    assertion prove a join rather than a coincidence.
    """
    token = await make_actor("byline@example.com")
    await ask(client, token)
    listed = await client.get("/api/v1/community/questions", headers=bearer(token))
    assert listed.json()["items"][0]["author_name"] == "byline@example.com"


async def test_one_question_opens_by_id_however_old_it_is(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """There was no single-question read, so a thread was hunted through the
    feed page — which meant anything past the first hundred 404ed on a link."""
    token = await make_actor("deeplink@example.com")
    question = await ask(client, token, title="Deep-linked")

    response = await client.get(f"/api/v1/community/questions/{question['id']}", headers=bearer(token))
    assert response.status_code == 200, response.text
    assert response.json()["id"] == question["id"]
    assert response.json()["title"] == "Deep-linked"


async def test_an_answer_is_listed_across_every_question(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Replies were only readable one question at a time, so "answers I wrote"
    cost a request per question and the screen shipped empty."""
    asker = await make_actor("asker@example.com")
    responder = await make_actor("responder@example.com")
    first = await ask(client, asker, title="First")
    second = await ask(client, asker, title="Second")

    for question, body in ((first, "History first."), (second, "Examine, then plan.")):
        posted = await client.post(
            f"/api/v1/community/questions/{question['id']}/replies",
            json={"body": body},
            headers=bearer(responder),
        )
        assert posted.status_code == 201, posted.text

    mine = await client.get("/api/v1/community/replies?author=me", headers=bearer(responder))
    assert mine.status_code == 200, mine.text
    assert sorted(item["body"] for item in mine.json()["items"]) == [
        "Examine, then plan.",
        "History first.",
    ]
    # Only their own answers, not the whole pool.
    other = await client.get("/api/v1/community/replies?author=me", headers=bearer(asker))
    assert other.json()["items"] == []


async def test_the_author_filter_refuses_to_read_somebody_else(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """`author` takes `me` and nothing else: another person's answer history is
    a different question, with its own visibility rule this endpoint has not."""
    token = await make_actor("nosy@example.com")
    response = await client.get("/api/v1/community/replies?author=someone-else", headers=bearer(token))
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_author_filter"


async def test_the_feed_can_narrow_to_my_questions(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """`mine` filters in SQL, so the tab is not "the first page, minus the rows
    that were not mine"."""
    mine = await make_actor("mine-asker@example.com")
    theirs = await make_actor("theirs-asker@example.com")
    await ask(client, mine, title="Mine")
    await ask(client, theirs, title="Theirs")

    response = await client.get("/api/v1/community/questions?mine=true", headers=bearer(mine))
    assert [item["title"] for item in response.json()["items"]] == ["Mine"]
