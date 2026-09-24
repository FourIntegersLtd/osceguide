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
    from app.features.media.service_search import get_vector_index

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


async def test_a_platform_admin_reads_bodies_on_the_listing(
    client: AsyncClient, make_actor, index: FakeVectorIndex
) -> None:  # type: ignore[no-untyped-def]
    """The episode player loads its playlist from GET /media, not the slug read.

    A slug read already unlocks for staff. If the listing stayed locked, the
    page would show the title and 'this episode has no audio attached yet'.
    """
    from tests.support.catalog import create_exam

    admin = await make_actor("m-admin-list@osceguide.com", platform_admin=True)
    await create_exam(client, admin, code="sca")
    item = await an_exam_item(client, admin, exam_code="sca", title="SCA Deck For Staff")

    listed = (await client.get("/api/v1/media?kind=slide_deck", headers=bearer(admin))).json()["items"]
    row = next(entry for entry in listed if entry["id"] == item["id"])
    assert row["locked"] is False
    assert row["content"] == {"slides": ["Angina", "Reflux"]}


async def publish_item(
    client: AsyncClient,
    admin: str,
    *,
    title: str,
    kind: str = "summary",
    summary: str | None = None,
    content: dict | None = None,
    exam_code: str | None = None,
) -> dict:
    """A published item, authored the way the staff console authors one."""
    payload: dict = {"kind": kind, "title": title}
    if summary is not None:
        payload["summary"] = summary
    if content is not None:
        payload["content"] = content
    if exam_code is not None:
        payload["exam_code"] = exam_code
    created = await client.post("/api/v1/media", json=payload, headers=bearer(admin))
    assert created.status_code == 201, created.text
    published = await client.post(f"/api/v1/media/{created.json()['id']}/publish", headers=bearer(admin))
    assert published.status_code == 200, published.text
    return created.json()


# --------------------------------------------------------------------------
# Filtering the catalogue in SQL
#
# `exam_code` and `q` were the browser's job: the library was pulled down six
# pages at a time and narrowed in memory, so "no matches" meant "not in the
# first six hundred" and an exam-scoped list cost the transfer of every exam's
# material. Both are answered by the query now, which is what makes that walk
# of the whole catalogue unnecessary.
# --------------------------------------------------------------------------


async def test_exam_code_narrows_the_listing(
    client: AsyncClient,
    make_actor,
    index: FakeVectorIndex,  # type: ignore[no-untyped-def]
) -> None:
    """Another exam's material goes; free material stays.

    Material tagged with no exam belongs on every exam's list — that is what
    the consumer screens showed, and a filter that dropped it would empty the
    free half of the library from every tab.
    """
    from tests.support.catalog import create_exam

    admin = await make_actor("m-exam-filter@osceguide.com", platform_admin=True)
    await create_exam(client, admin, code="sca")
    await create_exam(client, admin, code="plab")
    await publish_item(client, admin, title="SCA Only Deck", kind="slide_deck", exam_code="sca")
    await publish_item(client, admin, title="PLAB Only Deck", kind="slide_deck", exam_code="plab")
    await publish_item(client, admin, title="Free For Everyone", kind="blog")

    body = (await client.get("/api/v1/media?exam_code=sca", headers=bearer(admin))).json()

    assert {item["title"] for item in body["items"]} == {"SCA Only Deck", "Free For Everyone"}
    assert body["total_count"] == 2


async def test_an_exam_code_that_names_no_exam_is_refused(
    client: AsyncClient,
    make_actor,  # type: ignore[no-untyped-def]
) -> None:
    """Refused rather than answered with the free material alone.

    Silently widening a filter a client asked for is how a screen comes to
    show one exam's library and call it another's.
    """
    admin = await make_actor("m-exam-unknown@osceguide.com", platform_admin=True)

    response = await client.get("/api/v1/media?exam_code=nope", headers=bearer(admin))

    assert response.status_code == 404
    assert response.json()["code"] == "unknown_exam"


async def test_q_matches_a_title_and_a_summary(
    client: AsyncClient,
    make_actor,
    index: FakeVectorIndex,  # type: ignore[no-untyped-def]
) -> None:
    admin = await make_actor("m-q@osceguide.com", platform_admin=True)
    await publish_item(client, admin, title="Chest Pain Basics", summary="How to approach it.")
    await publish_item(client, admin, title="Headache", summary="Red flags include sudden chest pain.")
    await publish_item(client, admin, title="Abdominal Exam", summary="Nothing in common with the term.")

    body = (await client.get("/api/v1/media?q=chest", headers=bearer(admin))).json()

    # One by its title, one by its summary, and the unrelated row in neither.
    assert sorted(item["title"] for item in body["items"]) == ["Chest Pain Basics", "Headache"]
    assert body["total_count"] == 2

    # Case-insensitive, because a search box is not a place to mind your caps.
    shouted = (await client.get("/api/v1/media?q=CHEST", headers=bearer(admin))).json()
    assert shouted["total_count"] == 2


async def test_a_q_that_matches_nothing_says_so(
    client: AsyncClient,
    make_actor,
    index: FakeVectorIndex,  # type: ignore[no-untyped-def]
) -> None:
    admin = await make_actor("m-q-none@osceguide.com", platform_admin=True)
    await publish_item(client, admin, title="Chest Pain Basics", summary="How to approach it.")

    body = (await client.get("/api/v1/media?q=zzznothing", headers=bearer(admin))).json()

    assert body["items"] == []
    assert body["total_count"] == 0


async def test_total_count_counts_the_match_not_the_page(
    client: AsyncClient,
    make_actor,
    index: FakeVectorIndex,  # type: ignore[no-untyped-def]
) -> None:
    """The number a screen prints as "N found", which a page cannot give.

    `items` says what this page holds. Printing its length announced "2 found"
    for a library of three, and got worse as the library grew past a page.
    """
    admin = await make_actor("m-count@osceguide.com", platform_admin=True)
    for name in ("Alpha", "Beta", "Gamma"):
        await publish_item(client, admin, title=f"Counted {name}")

    first = (await client.get("/api/v1/media?limit=2", headers=bearer(admin))).json()
    assert len(first["items"]) == 2
    assert first["total_count"] == 3
    assert first["next_cursor"]

    second = (
        await client.get(f"/api/v1/media?limit=2&cursor={first['next_cursor']}", headers=bearer(admin))
    ).json()
    assert len(second["items"]) == 1
    # The whole match, not the remainder: the count does not move as you page.
    assert second["total_count"] == 3
    assert second["next_cursor"] is None


# --------------------------------------------------------------------------
# Fields the read model carries but no column does
#
# `specialty` and `updated_at` live inside the document-shaped `content`, so a
# screen that wanted either had to know the authoring payload's shape — and
# got nothing at all for an item the reader had not unlocked, whose `content`
# is withheld.
# --------------------------------------------------------------------------


async def test_specialty_and_updated_at_come_from_the_document(
    client: AsyncClient,
    make_actor,
    index: FakeVectorIndex,  # type: ignore[no-untyped-def]
) -> None:
    admin = await make_actor("m-derived@osceguide.com", platform_admin=True)
    item = await publish_item(
        client,
        admin,
        title="Filing Cabinet",
        content={
            # The list is what the staff facets read, and it wins — the same
            # precedence the retiring client's own reader used.
            "specialties": ["Cardiology", "Respiratory"],
            "specialty": "Respiratory",
            "updated_at": "2024-05-01T10:00:00Z",
        },
    )

    body = (await client.get(f"/api/v1/media/{item['slug']}", headers=bearer(admin))).json()

    assert body["specialty"] == "Cardiology"
    assert body["updated_at"] == "2024-05-01T10:00:00Z"

    listed = (await client.get("/api/v1/media", headers=bearer(admin))).json()["items"]
    row = next(entry for entry in listed if entry["id"] == item["id"])
    assert row["specialty"] == "Cardiology"
    assert row["updated_at"] == "2024-05-01T10:00:00Z"

    naive = await publish_item(
        client, admin, title="Naive Date", content={"updated_at": "2023-01-02T03:04:05"}
    )
    naive_body = (await client.get(f"/api/v1/media/{naive['slug']}", headers=bearer(admin))).json()
    # A document date that never named its zone is read as UTC, so the field is
    # comparable with every other timestamp this API serves.
    assert naive_body["updated_at"] == "2023-01-02T03:04:05Z"


async def test_specialty_and_updated_at_fall_back_when_the_document_has_neither(
    client: AsyncClient,
    make_actor,
    index: FakeVectorIndex,  # type: ignore[no-untyped-def]
) -> None:
    admin = await make_actor("m-derived-none@osceguide.com", platform_admin=True)
    item = await publish_item(client, admin, title="Nothing Filed", content={"slides": ["Angina"]})

    body = (await client.get(f"/api/v1/media/{item['slug']}", headers=bearer(admin))).json()

    assert body["specialty"] is None
    # No date in the document, so the row's own: for an item nobody has edited
    # since it was written, that is the moment it was created. Never null, so a
    # screen can sort a list by it without a branch per row.
    assert body["updated_at"] == body["created_at"]


async def test_a_locked_item_still_reports_its_specialty(
    client: AsyncClient,
    make_actor,
    index: FakeVectorIndex,  # type: ignore[no-untyped-def]
) -> None:
    """A facet is catalogue metadata, not the paid body.

    Withheld with the body, and the locked deck would vanish from the specialty
    facet on the very screen that offers to unlock it.
    """
    from tests.support.catalog import create_exam

    admin = await make_actor("m-locked-facet@osceguide.com", platform_admin=True)
    await create_exam(client, admin, code="sca")
    item = await publish_item(
        client,
        admin,
        title="Locked Facet",
        kind="slide_deck",
        exam_code="sca",
        content={"specialties": ["Cardiology"], "slides": ["Angina"]},
    )

    reader = await make_actor("m-locked-facet-reader@example.com")
    body = (await client.get(f"/api/v1/media/{item['slug']}", headers=bearer(reader))).json()

    assert body["locked"] is True
    assert body["content"] is None
    assert body["specialty"] == "Cardiology"


# --------------------------------------------------------------------------
# Search: a kind filter, an excerpt, and a page that continues
# --------------------------------------------------------------------------


async def test_search_filters_by_kind(
    client: AsyncClient,
    make_actor,
    index: FakeVectorIndex,  # type: ignore[no-untyped-def]
) -> None:
    admin = await make_actor("m-kind-search@osceguide.com", platform_admin=True)
    await publish_item(client, admin, title="Kind Filter Deck", kind="slide_deck", summary="Revise it.")
    await publish_item(client, admin, title="Kind Filter Summary", kind="summary", summary="Revise it.")
    reader = await make_actor("m-kind-search-reader@example.com")

    unfiltered = (await client.get("/api/v1/media-search?q=kind filter", headers=bearer(reader))).json()
    assert unfiltered["total_count"] == 2

    body = (
        await client.get("/api/v1/media-search?q=kind filter&kind=slide_deck", headers=bearer(reader))
    ).json()

    assert [hit["slug"] for hit in body["items"]] == ["kind-filter-deck"]
    assert body["total_count"] == 1


async def test_search_refuses_a_kind_that_is_not_one(
    client: AsyncClient,
    make_actor,
    index: FakeVectorIndex,  # type: ignore[no-untyped-def]
) -> None:
    token = await make_actor("m-bad-kind@example.com")

    response = await client.get("/api/v1/media-search?q=chest&kind=video", headers=bearer(token))

    assert response.status_code == 422
    assert response.json()["code"] == "unknown_media_kind"


async def test_a_search_hit_carries_an_excerpt(
    client: AsyncClient,
    make_actor,
    index: FakeVectorIndex,  # type: ignore[no-untyped-def]
) -> None:
    admin = await make_actor("m-excerpt@osceguide.com", platform_admin=True)
    await publish_item(client, admin, title="Excerpt With Summary", summary="  A   long  summary.  ")
    await publish_item(client, admin, title="Excerpt Without Summary")
    reader = await make_actor("m-excerpt-reader@example.com")

    body = (await client.get("/api/v1/media-search?q=excerpt", headers=bearer(reader))).json()
    hits = {hit["slug"]: hit for hit in body["items"]}

    # The summary, with its whitespace collapsed: a result row is not the place
    # to render an authoring payload's line breaks.
    assert hits["excerpt-with-summary"]["excerpt"] == "A long summary."
    # And the title for an item that has no summary, so a result is never a
    # title with nothing under it.
    assert hits["excerpt-without-summary"]["excerpt"] == "Excerpt Without Summary"


async def test_search_pages_through_every_hit_exactly_once(
    client: AsyncClient,
    make_actor,
    index: FakeVectorIndex,  # type: ignore[no-untyped-def]
) -> None:
    """A `next_cursor` that continues, rather than the hard-coded null it was.

    Keyset on `(score, id)`: hits that share a score — which is every hit from
    an index that ranks coarsely — still come back in one order, so a page
    boundary neither repeats a hit the reader has seen nor skips the next one.
    """
    admin = await make_actor("m-paging@osceguide.com", platform_admin=True)
    names = ("One", "Two", "Three", "Four", "Five")
    for name in names:
        await publish_item(client, admin, title=f"Paging {name}", summary="Keyset paging fixture.")
    reader = await make_actor("m-paging-reader@example.com")

    url = "/api/v1/media-search?q=paging&limit=2"
    body = (await client.get(url, headers=bearer(reader))).json()
    assert len(body["items"]) == 2
    assert body["total_count"] == 5
    assert body["next_cursor"], "a first page of two out of five has more after it"

    seen = [hit["slug"] for hit in body["items"]]
    cursor = body["next_cursor"]
    pages = 1
    while cursor:
        page = (await client.get(f"{url}&cursor={cursor}", headers=bearer(reader))).json()
        seen.extend(hit["slug"] for hit in page["items"])
        assert page["total_count"] == 5
        cursor = page["next_cursor"]
        pages += 1
        assert pages < 10, "the cursor never ran out"

    assert len(seen) == len(set(seen)), f"a hit was served twice: {seen}"
    assert set(seen) == {f"paging-{name.lower()}" for name in names}, "a hit was skipped"
