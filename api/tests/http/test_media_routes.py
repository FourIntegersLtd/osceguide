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
