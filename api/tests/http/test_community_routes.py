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


# -------------------------------------------------------------------- tags


async def ask_tagged(client: AsyncClient, token: str, title: str, tags: list[str]) -> dict:
    response = await client.post(
        "/api/v1/community/questions",
        json={"title": title, "body": "Tagged question.", "tags": tags},
        headers=bearer(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_a_question_carries_its_tags(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The feature the ported screens had to drop: an asker tags a question
    and the feed shows the tags. Normalized on write — trimmed, lowercased,
    de-duplicated, blanks dropped — so what reads back is what the filter
    matches."""
    token = await make_actor("tagger@example.com")
    asked = await ask_tagged(client, token, "Chest pain", ["  Cardiology ", "cardiology", "", "neurology"])
    assert asked["tags"] == ["cardiology", "neurology"]

    listed = await client.get("/api/v1/community/questions", headers=bearer(token))
    assert listed.json()["items"][0]["tags"] == ["cardiology", "neurology"]


async def test_a_question_without_tags_reads_back_an_empty_list(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("untagged@example.com")
    asked = await ask(client, token)
    assert asked["tags"] == []


async def test_an_over_long_tag_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("verbose@example.com")
    response = await client.post(
        "/api/v1/community/questions",
        json={"title": "T", "body": "B", "tags": ["x" * 33]},
        headers=bearer(token),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "tag_too_long"


async def test_too_many_tags_are_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Refused rather than truncated: posting a question tagged differently
    from what its author asked is the silent wrong answer."""
    token = await make_actor("hoarder@example.com")
    response = await client.post(
        "/api/v1/community/questions",
        json={"title": "T", "body": "B", "tags": [f"tag-{i}" for i in range(6)]},
        headers=bearer(token),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "too_many_tags"


async def test_a_reply_carries_no_tags(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """A reply belongs to its question's thread and topic, the way it belongs
    to its question's audience: tags sent on a reply are refused by having
    nowhere to go, and the reply reads back with none."""
    asker = await make_actor("tag-asker@example.com")
    responder = await make_actor("tag-responder@example.com")
    question = await ask_tagged(client, asker, "Tagged thread", ["cardiology"])

    reply = await client.post(
        f"/api/v1/community/questions/{question['id']}/replies",
        json={"body": "History first.", "tags": ["surgery"]},
        headers=bearer(responder),
    )
    assert reply.status_code == 201, reply.text
    assert reply.json()["tags"] == []

    # The question keeps its own.
    detail = await client.get(f"/api/v1/community/questions/{question['id']}", headers=bearer(asker))
    assert detail.json()["tags"] == ["cardiology"]


async def test_the_feed_narrows_to_one_tag(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("filterer@example.com")
    await ask_tagged(client, token, "Heart", ["cardiology"])
    await ask_tagged(client, token, "Brain", ["neurology"])
    await ask(client, token, title="Untagged")

    filtered = await client.get("/api/v1/community/questions?tag=cardiology", headers=bearer(token))
    assert [item["title"] for item in filtered.json()["items"]] == ["Heart"]

    # The filter is normalized the way tags are stored, so casing and
    # padding on the query do not change the answer.
    sloppy = await client.get("/api/v1/community/questions?tag=%20Cardiology%20", headers=bearer(token))
    assert [item["title"] for item in sloppy.json()["items"]] == ["Heart"]


async def test_the_tag_filter_never_widens_what_a_caller_may_see(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor
) -> None:
    """An institution's tagged question stays invisible to an outsider who
    happens to know the tag: the filter is one more AND on top of visibility,
    never a way around it."""
    from tests.http.test_audiences import a_member, an_org, org_audience

    org_id, _ = await an_org(client, make_actor, "tags-leak")
    member = await a_member(make_actor, org_id, "tags-leak", "tag-member@example.com")
    outsider = await make_actor("tag-outsider@example.com")

    asked = await client.post(
        "/api/v1/community/questions",
        json={
            "title": "Ward round",
            "body": "Internal.",
            "tags": ["ward-round"],
            "audience": org_audience(org_id),
        },
        headers=bearer(member),
    )
    assert asked.status_code == 201, asked.text

    inside = await client.get("/api/v1/community/questions?tag=ward-round", headers=bearer(member))
    assert "Ward round" in [q["title"] for q in inside.json()["items"]]

    outside = await client.get("/api/v1/community/questions?tag=ward-round", headers=bearer(outsider))
    assert outside.json()["items"] == []


async def test_a_row_from_before_the_tags_column_reads_back_with_an_empty_list(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    """The migration's promise, tested the way production meets it: a row
    inserted without naming `tags` — what every existing row was — gets the
    column default and reads as `[]`, not NULL where the schema expects a
    list."""
    from sqlalchemy import text

    token = await make_actor("premigration@example.com")
    mine = await ask(client, token)

    await db_session.execute(
        text(
            "INSERT INTO posts (id, kind, author_id, title, body, visibility) "
            "VALUES (gen_random_uuid(), 'question', :author, 'Legacy row', 'Written "
            "before tags existed.', 'public')"
        ),
        {"author": uuid.UUID(mine["author_id"])},
    )
    await db_session.flush()

    listed = await client.get("/api/v1/community/questions", headers=bearer(token))
    legacy = next(item for item in listed.json()["items"] if item["title"] == "Legacy row")
    assert legacy["tags"] == []


async def test_asking_in_a_loop_is_refused_per_person(
    client: AsyncClient, make_actor, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    """E-23: a question is read by everybody, so a script posting them is cut off
    at the `publish` allowance — and someone else can still ask."""
    from app.core.rate_limit import PUBLISH
    from tests.http.test_mfa_routes import CountingRedis

    counter = CountingRedis()
    monkeypatch.setattr("app.core.rate_limit.get_redis", lambda: counter)
    spammer = await make_actor("loop@example.com")
    for number in range(PUBLISH.allowance):
        await ask(client, spammer, title=f"Question {number}")

    refused = await client.post(
        "/api/v1/community/questions",
        json={"title": "One more", "body": "I am stuck on chest pain stations."},
        headers=bearer(spammer),
    )
    assert refused.status_code == 429, refused.text
    assert refused.json()["code"] == "too_many_requests"
    assert refused.json()["details"]["limit"] == "publish"

    await ask(client, await make_actor("someone-else@example.com"), title="Mine")


async def test_the_moderation_queue_pages_past_one_page_and_names_the_author(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("c-mod@osceguide.com", platform_admin=True)
    author = await make_actor("c-mod-author@example.com")
    for number in range(3):
        await ask(client, author, title=f"Question {number}")

    first = (await client.get("/api/v1/platform/moderation/posts?limit=2", headers=bearer(admin))).json()
    assert len(first["items"]) == 2
    assert first["next_cursor"] is not None
    assert first["items"][0]["author_name"] is not None or first["items"][0]["author_id"]

    rest = (
        await client.get(
            f"/api/v1/platform/moderation/posts?limit=2&cursor={first['next_cursor']}", headers=bearer(admin)
        )
    ).json()
    assert len(rest["items"]) == 1
    assert rest["next_cursor"] is None
    titles = {post["title"] for post in first["items"] + rest["items"]}
    assert titles == {"Question 0", "Question 1", "Question 2"}
