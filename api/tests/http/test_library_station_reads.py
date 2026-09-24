"""Reading one library station, searching the library, and reading a history.

The three reads the platform library was missing. A station could be listed and
a set could bind its version, and that was all: a shared link was answered by
walking the browse pages in the browser, a typed search term could only match
what had already been fetched, and nothing at all answered "what revisions has
this station been through" — every one of those is a question a screen asks and
used to answer for itself.

What the first two must not do is hand over the document. The library is
browsable by everyone signed in, and the document is the patient's persona and
the examiner's material, so a per-station read answers with the same row the
list gives and no more. The third is the author's view and is staff-only for
exactly that reason.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.http.test_stations_routes import (
    CONTENT,
    a_browser,
    a_library_station,
    make_station,
    member,
    seed_org,
)
from tests.support.catalog import ensure_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

# --------------------------------------------------------------------------
# GET /api/v1/stations/{station_id}
# --------------------------------------------------------------------------


async def test_a_library_station_answers_for_itself(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The deep link, without the catalogue walk.

    `findLibraryStation` in the new client fetched up to twenty pages to answer
    this; the route answers it in one read, with the same row a page would have
    given — which is what makes the walk deletable rather than merely slower.
    """
    token = await a_browser(db_session, make_actor, "link@example.com")
    station_id = await a_library_station(db_session, "Chest pain")

    response = await client.get(f"/api/v1/stations/{station_id}", headers=bearer(token))

    assert response.status_code == 200, response.text
    row = response.json()
    assert row["id"] == str(station_id)
    assert row["title"] == "Chest pain"
    assert row["exam_code"] == "sca"
    assert row["version"] == 1
    # The version a practice set or a circuit binds, resolved server-side.
    assert uuid.UUID(row["version_id"])


async def test_a_link_answers_with_no_answers(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Opening a station is not reading the document.

    The content is the brief, the patient's hidden history and the marking
    guidance. A candidate reads the brief through their own attempt, once one
    exists; a link to a station discloses nothing.
    """
    token = await a_browser(db_session, make_actor, "quiet@example.com")
    station_id = await a_library_station(db_session, "A sore ankle")

    row = (await client.get(f"/api/v1/stations/{station_id}", headers=bearer(token))).json()

    assert "content" not in row
    assert set(row) == {"id", "title", "exam_code", "version_id", "version", "published_at"}


async def test_the_library_is_the_only_thing_this_route_reads(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    """An institution's own station is not in the library, published or not.

    Asked by the station's own admin, so the answer cannot be an oversight
    about who was calling: this route reads the platform's half of the table
    and nothing else.
    """
    org_id = await seed_org(client, make_actor)
    admin = await member(make_actor, org_id, "kings", "owner")
    theirs = await make_station(client, admin, content=CONTENT)
    await client.post(f"/api/v1/orgs/kings/stations/{theirs['id']}/versions/1/publish", headers=bearer(admin))

    as_stranger = await client.get(f"/api/v1/stations/{theirs['id']}", headers=bearer(admin))
    assert as_stranger.status_code == 404
    assert as_stranger.json()["code"] == "station_not_found"


async def test_an_unpublished_library_station_is_not_in_the_library(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    """A draft in the platform's own half answers the same way, for the same reason."""
    await ensure_exam(db_session, "sca")
    root = await make_actor("curator@example.com", platform_admin=True)
    drafted = await client.post(
        "/api/v1/platform/stations",
        json={"title": "Not finished", "exam_code": "sca", "content": CONTENT},
        headers=bearer(root),
    )
    assert drafted.status_code == 201, drafted.text
    browser = await a_browser(db_session, make_actor, "peeker@example.com")

    response = await client.get(f"/api/v1/stations/{drafted.json()['id']}", headers=bearer(browser))
    assert response.status_code == 404
    assert response.json()["code"] == "station_not_found"


async def test_a_platform_admin_reads_a_station_of_any_exam(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    """Curating the catalogue means opening a station in any part of it."""
    await ensure_exam(db_session, "casc")
    elsewhere = await a_library_station(db_session, "A psych case", exam_code="casc")
    root = await make_actor("curator2@example.com", platform_admin=True)

    response = await client.get(f"/api/v1/stations/{elsewhere}", headers=bearer(root))

    assert response.status_code == 200, response.text
    assert response.json()["exam_code"] == "casc"


async def test_a_station_outside_the_exams_you_may_open_is_refused(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The same scoping the browse page has, on a route that cannot name an exam.

    Without it, `GET /stations/{id}` is the hole in the exam scoping: the list
    would hold back another exam's titles and a link would hand them over.
    """
    await ensure_exam(db_session, "casc")
    elsewhere = await a_library_station(db_session, "A psych case", exam_code="casc")
    gp = await a_browser(db_session, make_actor, "gp-only@example.com", exam_code="sca")

    refused = await client.get(f"/api/v1/stations/{elsewhere}", headers=bearer(gp))
    assert refused.status_code == 403, refused.text
    assert refused.json()["code"] == "not_entitled"


async def test_the_per_station_read_needs_a_token(client: AsyncClient) -> None:
    assert (await client.get(f"/api/v1/stations/{uuid.uuid4()}")).status_code == 401


# --------------------------------------------------------------------------
# GET /api/v1/stations?search=
# --------------------------------------------------------------------------


async def test_search_narrows_in_the_database_not_on_the_screen(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The term matches rows that a page never reached.

    Two questions in one assertion: the term matches only the titles it should,
    and it matches them at all when the page size is smaller than the catalogue
    ahead of the match — which is what a screen paging a hundred rows at a time
    and filtering what arrived could not do.
    """
    token = await a_browser(db_session, make_actor, "searcher@example.com")
    await a_library_station(db_session, "Chest pain")
    await a_library_station(db_session, "Headache")
    wheezy = await a_library_station(db_session, "Wheezy child")

    page = await client.get("/api/v1/stations?search=wheezy", headers=bearer(token))
    assert page.status_code == 200, page.text
    assert [row["title"] for row in page.json()["items"]] == ["Wheezy child"]

    # One row per page, and the match is still found third in the catalogue.
    tight = await client.get("/api/v1/stations?search=WHEEZY%20child&limit=1", headers=bearer(token))
    assert [row["id"] for row in tight.json()["items"]] == [str(wheezy)]

    partial = await client.get("/api/v1/stations?search=eezy", headers=bearer(token))
    assert [row["title"] for row in partial.json()["items"]] == ["Wheezy child"]

    nothing = await client.get("/api/v1/stations?search=fracture", headers=bearer(token))
    assert nothing.json()["items"] == []


async def test_an_empty_term_is_no_term(client: AsyncClient, make_actor, db_session: AsyncSession) -> None:
    token = await a_browser(db_session, make_actor, "blank-search@example.com")
    await a_library_station(db_session, "Chest pain")
    await a_library_station(db_session, "Headache")

    blank = await client.get("/api/v1/stations?search=", headers=bearer(token))
    spaced = await client.get("/api/v1/stations?search=%20%20", headers=bearer(token))

    assert {row["title"] for row in blank.json()["items"]} == {"Chest pain", "Headache"}
    assert {row["title"] for row in spaced.json()["items"]} == {"Chest pain", "Headache"}


async def test_search_stays_inside_the_library_and_the_exam(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """A term is a narrowing, never a widening.

    An institution's own station with a matching title is not in the library,
    and another exam's library station is not in the caller's.
    """
    org_id = await seed_org(client, make_actor)
    admin = await member(make_actor, org_id, "kings", "owner")
    await make_station(client, admin)  # titled "Chest pain", the same as the library's
    token = await a_browser(db_session, make_actor, "narrow@example.com")
    await a_library_station(db_session, "Chest pain")
    await ensure_exam(db_session, "casc")
    await a_library_station(db_session, "Chest pain in a psych patient", exam_code="casc")

    rows = (await client.get("/api/v1/stations?search=pain", headers=bearer(token))).json()["items"]

    assert [row["title"] for row in rows] == ["Chest pain"]
    assert all(row["exam_code"] == "sca" for row in rows)


# --------------------------------------------------------------------------
# GET /api/v1/stations/{station_id}/versions
# --------------------------------------------------------------------------


async def an_authored_station_with_three_revisions(
    client: AsyncClient, admin: str, slug: str = "kings"
) -> str:
    """A draft, a published revision and an archived one, in that order of status."""
    station = await make_station(client, admin, slug=slug)
    station_id = station["id"]
    url = f"/api/v1/orgs/{slug}/stations/{station_id}/versions"
    await client.post(f"{url}/1/publish", headers=bearer(admin))
    await client.post(url, headers=bearer(admin))  # version 2, drafted from version 1
    await client.post(f"{url}/1/archive", headers=bearer(admin))
    return station_id


async def test_the_history_lists_every_revision_newest_first(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The lifecycle had writes and no reader.

    A station could be drafted, published, superseded and archived and nothing
    listed what came of it, so an author could not read a superseded revision
    back. Whole documents, which is the price of being staff.
    """
    org_id = await seed_org(client, make_actor)
    admin = await member(make_actor, org_id, "kings", "owner")
    station_id = await an_authored_station_with_three_revisions(client, admin)

    response = await client.get(f"/api/v1/stations/{station_id}/versions", headers=bearer(admin))

    assert response.status_code == 200, response.text
    rows = response.json()
    assert [row["version"] for row in rows] == [2, 1], "a history reads from the present backwards"
    assert [row["status"] for row in rows] == ["draft", "archived"]
    assert rows[0]["station_id"] == station_id
    assert rows[0]["content"] == CONTENT  # the draft seeded from version 1
    assert rows[1]["published_at"] is not None
    assert rows[1]["archived_at"] is not None


async def test_a_station_of_nothing_has_no_history(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("nobody@example.com", platform_admin=True)
    response = await client.get(f"/api/v1/stations/{uuid.uuid4()}/versions", headers=bearer(admin))
    assert response.status_code == 404
    assert response.json()["code"] == "station_not_found"


async def test_the_history_is_staff_and_not_the_rest_of_the_org(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Every rostered reader may list the org's stations; this lists their documents.

    A trainee already gets the candidate-facing projection of the current
    version, and a supervisor may read the one they mark. Every *revision* —
    including the withdrawn ones, with the material that got them withdrawn —
    is the author's, and refusing a member who is not an admin is the same
    answer the org routes give when membership is not the role that asks.
    """
    org_id = await seed_org(client, make_actor)
    admin = await member(make_actor, org_id, "kings", "owner")
    station_id = await an_authored_station_with_three_revisions(client, admin)

    for role in ("trainee", "supervisor", "practice_user"):
        reader = await member(make_actor, org_id, "kings", role)
        response = await client.get(f"/api/v1/stations/{station_id}/versions", headers=bearer(reader))
        assert response.status_code == 403, role
        assert response.json()["code"] == "forbidden"

    outsider = await make_actor("elsewhere@example.com")
    assert (
        await client.get(f"/api/v1/stations/{station_id}/versions", headers=bearer(outsider))
    ).status_code == 403
    assert (await client.get(f"/api/v1/stations/{station_id}/versions")).status_code == 401


async def test_another_orgs_admin_may_not_read_the_history(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    kings = await seed_org(client, make_actor, "kings")
    guys = await seed_org(client, make_actor, "guys")
    station_id = await an_authored_station_with_three_revisions(
        client, await member(make_actor, kings, "kings", "owner")
    )
    rival = await member(make_actor, guys, "guys", "owner")

    response = await client.get(f"/api/v1/stations/{station_id}/versions", headers=bearer(rival))

    assert response.status_code == 403, response.text
    assert response.json()["code"] == "forbidden"


async def test_the_platform_admin_reads_any_stations_history(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The library is theirs to curate and an institution's catalogue to support."""
    org_id = await seed_org(client, make_actor)
    station_id = await an_authored_station_with_three_revisions(
        client, await member(make_actor, org_id, "kings", "owner")
    )
    library = await a_library_station(db_session, "Chest pain")
    staff = await make_actor("curator@example.com", platform_admin=True)

    own = await client.get(f"/api/v1/stations/{library}/versions", headers=bearer(staff))
    assert own.status_code == 200, own.text
    assert [row["status"] for row in own.json()] == ["published"]

    theirs = await client.get(f"/api/v1/stations/{station_id}/versions", headers=bearer(staff))
    assert theirs.status_code == 200, theirs.text
    assert [row["version"] for row in theirs.json()] == [2, 1]


async def test_an_org_admin_may_not_read_the_librarys_history(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Reading the catalogue is not the same as editing it, and neither is drafting."""
    org_id = await seed_org(client, make_actor)
    admin = await member(make_actor, org_id, "kings", "owner")
    library = await a_library_station(db_session, "Chest pain")

    response = await client.get(f"/api/v1/stations/{library}/versions", headers=bearer(admin))

    assert response.status_code == 403, response.text
    assert response.json()["code"] == "forbidden"
