"""Authoring, publishing and searching study material."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.support.fakes import FakeVectorIndex
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


@pytest.fixture
def index(client: AsyncClient) -> FakeVectorIndex:
    """Replace the search index with a fake, through the app's own seam."""
    from app.features.media.service import get_vector_index

    fake = FakeVectorIndex()
    client._transport.app.dependency_overrides[get_vector_index] = lambda: fake  # type: ignore[attr-defined]
    return fake


async def draft(client: AsyncClient, admin: str, title: str = "Chest Pain Basics") -> dict:
    response = await client.post(
        "/api/v1/media",
        json={"kind": "summary", "title": title, "summary": "How to approach chest pain."},
        headers=bearer(admin),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_a_draft_gets_a_readable_slug(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("m-admin@osceguide.com", platform_admin=True)
    item = await draft(client, admin)
    assert item["slug"] == "chest-pain-basics"
    assert item["status"] == "draft"


async def test_an_ordinary_user_cannot_author(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("m-user@example.com")
    response = await client.post(
        "/api/v1/media",
        json={"kind": "summary", "title": "Mine"},
        headers=bearer(token),
    )
    assert response.status_code == 403


async def test_a_duplicate_title_conflicts(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("m-dupe@osceguide.com", platform_admin=True)
    await draft(client, admin)
    response = await client.post(
        "/api/v1/media",
        json={"kind": "summary", "title": "chest pain basics"},
        headers=bearer(admin),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "slug_taken"


async def test_a_draft_is_not_found_by_an_ordinary_reader(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Its existence is not public either."""
    admin = await make_actor("m-hidden@osceguide.com", platform_admin=True)
    item = await draft(client, admin)
    reader = await make_actor("m-reader@example.com")

    response = await client.get(f"/api/v1/media/{item['slug']}", headers=bearer(reader))
    assert response.status_code == 404


async def test_publishing_makes_it_readable_and_findable(
    client: AsyncClient, make_actor, index: FakeVectorIndex
) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("m-pub@osceguide.com", platform_admin=True)
    item = await draft(client, admin)
    published = await client.post(f"/api/v1/media/{item['id']}/publish", headers=bearer(admin))
    assert published.json()["status"] == "published"
    assert item["id"] in index.documents

    reader = await make_actor("m-pub-reader@example.com")
    assert (await client.get(f"/api/v1/media/{item['slug']}", headers=bearer(reader))).status_code == 200


async def test_publishing_twice_conflicts(client: AsyncClient, make_actor, index: FakeVectorIndex) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("m-twice@osceguide.com", platform_admin=True)
    item = await draft(client, admin)
    url = f"/api/v1/media/{item['id']}/publish"
    await client.post(url, headers=bearer(admin))
    response = await client.post(url, headers=bearer(admin))
    assert response.status_code == 409
    assert response.json()["code"] == "media_already_published"


async def test_a_published_item_cannot_be_edited(
    client: AsyncClient, make_actor, index: FakeVectorIndex
) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("m-edit@osceguide.com", platform_admin=True)
    item = await draft(client, admin)
    await client.post(f"/api/v1/media/{item['id']}/publish", headers=bearer(admin))

    response = await client.patch(
        f"/api/v1/media/{item['id']}", json={"title": "Changed"}, headers=bearer(admin)
    )
    assert response.status_code == 409
    assert response.json()["code"] == "media_not_editable"


async def test_search_returns_published_matches(
    client: AsyncClient, make_actor, index: FakeVectorIndex
) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("m-search@osceguide.com", platform_admin=True)
    item = await draft(client, admin)
    await client.post(f"/api/v1/media/{item['id']}/publish", headers=bearer(admin))

    reader = await make_actor("m-search-reader@example.com")
    response = await client.get("/api/v1/media-search?q=chest", headers=bearer(reader))
    assert response.status_code == 200
    assert [hit["slug"] for hit in response.json()["items"]] == ["chest-pain-basics"]
    assert index.queries == ["chest"]


async def test_an_empty_search_is_refused(client: AsyncClient, make_actor, index: FakeVectorIndex) -> None:  # type: ignore[no-untyped-def]
    """Matching everything is expensive and useless."""
    token = await make_actor("m-empty@example.com")
    response = await client.get("/api/v1/media-search?q=%20%20", headers=bearer(token))
    assert response.status_code == 422
    assert response.json()["code"] == "empty_query"


async def test_search_does_not_leak_an_unpublished_item(
    client: AsyncClient, make_actor, index: FakeVectorIndex
) -> None:  # type: ignore[no-untyped-def]
    """The index holds ids; what a reader sees comes from the database, so a
    stale entry cannot surface something no longer published."""
    admin = await make_actor("m-stale@osceguide.com", platform_admin=True)
    item = await draft(client, admin, title="Stale Entry")
    await index.index(doc_id=item["id"], text="Stale Entry", metadata={})

    reader = await make_actor("m-stale-reader@example.com")
    response = await client.get("/api/v1/media-search?q=Stale", headers=bearer(reader))
    assert response.json()["items"] == []


# --------------------------------------------------------------------------
# Who may read the body
#
# The A to Z and the slide decks are the paid half of the consumer product and
# these routes returned them in full to anybody who asked — no token at all on
# the listing, and a token on the single read only to decide whether a *draft*
# existed. The titles stay public, because the landing page needs them and a
# shared link has to say what it points at; the body does not.
# --------------------------------------------------------------------------


async def an_exam_item(client: AsyncClient, admin: str, *, exam_code: str, title: str = "SCA Deck") -> dict:
    created = await client.post(
        "/api/v1/media",
        json={
            "kind": "slide_deck",
            "title": title,
            "summary": "What to revise.",
            "content": {"slides": ["Angina", "Reflux"]},
            "exam_code": exam_code,
        },
        headers=bearer(admin),
    )
    assert created.status_code == 201, created.text
    published = await client.post(f"/api/v1/media/{created.json()['id']}/publish", headers=bearer(admin))
    assert published.status_code == 200, published.text
    return created.json()


async def test_material_for_an_exam_is_locked_without_a_live_entitlement(
    client: AsyncClient, make_actor, db_session, index: FakeVectorIndex
) -> None:  # type: ignore[no-untyped-def]
    from tests.support.catalog import create_exam

    admin = await make_actor("m-lock@osceguide.com", platform_admin=True)
    await create_exam(client, admin, code="sca")
    item = await an_exam_item(client, admin, exam_code="sca")

    reader = await make_actor("m-lock-reader@example.com")
    response = await client.get(f"/api/v1/media/{item['slug']}", headers=bearer(reader))

    assert response.status_code == 200, response.text
    body = response.json()
    # Found, named, and not readable: the client shows the upgrade prompt the
    # retiring app showed rather than an empty article.
    assert body["title"] == "SCA Deck"
    assert body["locked"] is True
    assert body["content"] is None
    assert "Angina" not in str(body)


async def test_a_subscriber_reads_the_body(
    client: AsyncClient, make_actor, db_session, index: FakeVectorIndex
) -> None:  # type: ignore[no-untyped-def]
    from datetime import UTC, datetime, timedelta

    from app.features.entitlements import repository as ent_repo
    from app.features.identity import repository as identity_repo
    from tests.support.catalog import create_exam, ensure_exam

    admin = await make_actor("m-paid@osceguide.com", platform_admin=True)
    await create_exam(client, admin, code="sca")
    item = await an_exam_item(client, admin, exam_code="sca")

    reader = await make_actor("m-paid-reader@example.com")
    user = await identity_repo.user_by_email(db_session, "m-paid-reader@example.com")
    assert user is not None
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    await ent_repo.grant(
        session=db_session,
        user_id=user.id,
        exam_id=exam.id,
        source="purchase",
        ends_at=datetime.now(UTC) + timedelta(days=30),
    )
    await db_session.commit()

    body = (await client.get(f"/api/v1/media/{item['slug']}", headers=bearer(reader))).json()

    assert body["locked"] is False
    assert body["content"] == {"slides": ["Angina", "Reflux"]}


async def test_a_signed_out_visitor_gets_titles_but_no_body(
    client: AsyncClient, make_actor, index: FakeVectorIndex
) -> None:  # type: ignore[no-untyped-def]
    """The listing stays open, which is why the body had to stop being in it.

    A bearer was deliberately dropped from these routes so the landing page's
    article rail and shared links work signed out. That made every slide deck
    world-readable.
    """
    from tests.support.catalog import create_exam

    admin = await make_actor("m-anon@osceguide.com", platform_admin=True)
    await create_exam(client, admin, code="sca")
    item = await an_exam_item(client, admin, exam_code="sca")

    response = await client.get(f"/api/v1/media/{item['slug']}")

    assert response.status_code == 200
    assert response.json()["title"] == "SCA Deck"
    assert response.json()["content"] is None
    assert response.json()["locked"] is True


async def test_free_material_is_never_locked(client: AsyncClient, make_actor, index: FakeVectorIndex) -> None:  # type: ignore[no-untyped-def]
    """An item belonging to no exam is free material, and stays open to all."""
    admin = await make_actor("m-free@osceguide.com", platform_admin=True)
    item = await draft(client, admin, title="Welcome To OSCE Guide")
    await client.post(f"/api/v1/media/{item['id']}/publish", headers=bearer(admin))

    body = (await client.get(f"/api/v1/media/{item['slug']}")).json()

    assert body["locked"] is False
    assert body["content"] is not None


async def test_the_listing_locks_the_same_way(
    client: AsyncClient, make_actor, index: FakeVectorIndex
) -> None:  # type: ignore[no-untyped-def]
    from tests.support.catalog import create_exam

    admin = await make_actor("m-list@osceguide.com", platform_admin=True)
    await create_exam(client, admin, code="sca")
    await an_exam_item(client, admin, exam_code="sca", title="Locked Deck")

    reader = await make_actor("m-list-reader@example.com")
    items = (await client.get("/api/v1/media", headers=bearer(reader))).json()["items"]

    locked = [row for row in items if row["title"] == "Locked Deck"]
    assert locked, "the item is still listed"
    assert locked[0]["locked"] is True
    assert locked[0]["content"] is None
