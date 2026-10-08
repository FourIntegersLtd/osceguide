"""Reporting a station, and the queue staff work the reports from.

`POST /me/station-flags` was served by `identity` with the body thrown away and
a docstring saying persistence is TODO, while the button in the runner kept
confirming a report that had been discarded. These tests are the difference
between a button that answers and a button that works: the report has to be a
row, it has to be visible to the content team, and closing it has to stick.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.http.test_sittings_routes import org_with_admin
from tests.support.catalog import create_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

CONTENT = {"who_you_are": "Ben, 6.", "why_you_came": "Noisy breathing."}


async def a_station(client: AsyncClient, admin: str, slug: str = "kings") -> str:
    """One authored station, and its id rather than its version's."""
    created = await client.post(
        f"/api/v1/orgs/{slug}/stations",
        json={"title": "Wheezy child", "exam_code": "sca", "content": CONTENT},
        headers=bearer(admin),
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


# --- the reader's half ------------------------------------------------------


async def test_a_report_is_written_down(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    station_id = await a_station(client, admin)
    reader = await make_actor("reader-flag@example.com")

    reported = await client.post(
        "/api/v1/me/station-flags", json={"station_id": station_id}, headers=bearer(reader)
    )
    assert reported.status_code == 204, reported.text

    mine = await client.get("/api/v1/me/station-flags", headers=bearer(reader))
    assert mine.status_code == 200
    assert [(row["station_id"], row["station_title"], row["status"]) for row in mine.json()["items"]] == [
        (station_id, "Wheezy child", "open")
    ]


async def test_a_second_tap_is_the_same_report(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The legacy answer to a repeat was 400 "Station is already flagged", which
    the client surfaced as "we couldn't flag this station" over a report that
    had in fact been recorded. One tap, one row, whatever the button is told."""
    _, admin = await org_with_admin(client, make_actor)
    station_id = await a_station(client, admin)
    reader = await make_actor("twice-flag@example.com")

    for _ in range(2):
        assert (
            await client.post(
                "/api/v1/me/station-flags", json={"station_id": station_id}, headers=bearer(reader)
            )
        ).status_code == 204

    mine = await client.get("/api/v1/me/station-flags", headers=bearer(reader))
    assert len(mine.json()["items"]) == 1


async def test_two_readers_reporting_one_station_are_two_reports(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Counting the same complaint twice is the signal that a case needs a
    second look, so the dedupe is per person and not per station."""
    _, admin = await org_with_admin(client, make_actor)
    station_id = await a_station(client, admin)
    first = await make_actor("flag-one@example.com")
    second = await make_actor("flag-two@example.com")

    for reader in (first, second):
        await client.post("/api/v1/me/station-flags", json={"station_id": station_id}, headers=bearer(reader))

    root = await make_actor(f"queue-{uuid.uuid4().hex[:8]}@osceguide.com", platform_admin=True)
    queue = await client.get("/api/v1/platform/station-flags", headers=bearer(root))
    assert len(queue.json()["items"]) == 2


async def test_a_report_on_nothing_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    reader = await make_actor("stranger-flag@example.com")
    response = await client.post(
        "/api/v1/me/station-flags", json={"station_id": str(uuid.uuid4())}, headers=bearer(reader)
    )
    assert response.status_code == 404
    assert response.json()["code"] == "station_not_found"


async def test_nobody_signed_in_reports_nothing(client: AsyncClient) -> None:
    response = await client.post("/api/v1/me/station-flags", json={"station_id": str(uuid.uuid4())})
    assert response.status_code == 401


async def test_my_reports_can_be_searched_by_station_title(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The server does the same ILIKE the client used to do over every page it
    had already fetched, so a title outside the first page is still findable."""
    _, admin = await org_with_admin(client, make_actor)
    wheezy_id = await a_station(client, admin, slug="kings")
    sore_ankle = await client.post(
        "/api/v1/orgs/kings/stations",
        json={"title": "A sore ankle", "exam_code": "sca", "content": CONTENT},
        headers=bearer(admin),
    )
    assert sore_ankle.status_code == 201, sore_ankle.text
    reader = await make_actor("search-flag@example.com")
    for station_id in (wheezy_id, sore_ankle.json()["id"]):
        assert (
            await client.post(
                "/api/v1/me/station-flags", json={"station_id": station_id}, headers=bearer(reader)
            )
        ).status_code == 204

    narrowed = await client.get(
        "/api/v1/me/station-flags", params={"search": "wheezy"}, headers=bearer(reader)
    )

    assert narrowed.status_code == 200, narrowed.text
    assert [row["station_title"] for row in narrowed.json()["items"]] == ["Wheezy child"]


# --- the content team's half ------------------------------------------------


async def test_the_queue_names_the_station_and_the_reader(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The report is about a case and came from a person, so a queue that shows
    neither is a list of ids. The legacy screen resolved titles in the browser
    by listing every station it could, and printed "Unknown Station" whenever
    the case was not on the page it happened to have."""
    _, admin = await org_with_admin(client, make_actor)
    station_id = await a_station(client, admin)
    reader = await make_actor("queue-reader@example.com")
    await client.post(
        "/api/v1/me/station-flags",
        json={"station_id": station_id},
        headers=bearer(reader),
    )
    root = await make_actor(f"queue-{uuid.uuid4().hex[:8]}@osceguide.com", platform_admin=True)

    queue = await client.get("/api/v1/platform/station-flags", headers=bearer(root))
    assert queue.status_code == 200, queue.text
    row = queue.json()["items"][0]
    assert row["station_title"] == "Wheezy child"
    # The reader's own name, from the token the harness minted for them.
    assert row["reporter_name"] == "queue-reader@example.com"
    assert row["status"] == "open"


async def test_a_reader_may_not_work_the_queue(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    await org_with_admin(client, make_actor)
    reader = await make_actor("not-staff@example.com")
    response = await client.get("/api/v1/platform/station-flags", headers=bearer(reader))
    assert response.status_code == 403


async def test_closing_a_report_sticks_and_reopening_clears_it(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    station_id = await a_station(client, admin)
    reader = await make_actor("closer@example.com")
    await client.post("/api/v1/me/station-flags", json={"station_id": station_id}, headers=bearer(reader))
    root = await make_actor(f"queue-{uuid.uuid4().hex[:8]}@osceguide.com", platform_admin=True)
    flag_id = (await client.get("/api/v1/platform/station-flags", headers=bearer(root))).json()["items"][0][
        "id"
    ]

    closed = await client.patch(
        f"/api/v1/platform/station-flags/{flag_id}",
        json={"status": "resolved", "note": "Wording fixed in version 3."},
        headers=bearer(root),
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "resolved"
    assert closed.json()["resolved_at"] is not None
    assert closed.json()["resolution_note"] == "Wording fixed in version 3."

    # And the reader's own list says the same thing, so the button does not
    # invite them to file it again.
    mine = await client.get("/api/v1/me/station-flags", headers=bearer(reader))
    assert mine.json()["items"][0]["status"] == "resolved"

    reopened = await client.patch(
        f"/api/v1/platform/station-flags/{flag_id}",
        json={"status": "open"},
        headers=bearer(root),
    )
    assert reopened.json()["status"] == "open"
    assert reopened.json()["resolved_at"] is None, "an open row must not carry a resolution timestamp"

    only_open = await client.get(
        "/api/v1/platform/station-flags", params={"status": "open"}, headers=bearer(root)
    )
    assert [row["id"] for row in only_open.json()["items"]] == [flag_id]
    answered = await client.get(
        "/api/v1/platform/station-flags", params={"status": "resolved"}, headers=bearer(root)
    )
    assert answered.json()["items"] == []


async def test_closing_a_report_tells_the_reporter_on_closing_only(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    station_id = await a_station(client, admin)
    reader = await make_actor("told@example.com")
    await client.post("/api/v1/me/station-flags", json={"station_id": station_id}, headers=bearer(reader))
    root = await make_actor(f"queue-{uuid.uuid4().hex[:8]}@osceguide.com", platform_admin=True)
    flag_id = (await client.get("/api/v1/platform/station-flags", headers=bearer(root))).json()["items"][0][
        "id"
    ]
    url = f"/api/v1/platform/station-flags/{flag_id}"

    await client.patch(url, json={"status": "resolved", "note": "Wording fixed."}, headers=bearer(root))
    inbox = (await client.get("/api/v1/me/messages", headers=bearer(reader))).json()["items"]
    assert [(m["kind"], m["subject"], m["body"]) for m in inbox] == [
        ("report_answer", "About your report: Wheezy child", "Wording fixed.")
    ]

    # Editing the note of a closed report, and reopening it, say nothing new.
    await client.patch(url, json={"status": "resolved", "note": "Reworded."}, headers=bearer(root))
    await client.patch(url, json={"status": "open"}, headers=bearer(root))
    after = (await client.get("/api/v1/me/messages", headers=bearer(reader))).json()["items"]
    assert len(after) == 1


async def test_an_unknown_report_cannot_be_closed(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor(f"queue-{uuid.uuid4().hex[:8]}@osceguide.com", platform_admin=True)
    response = await client.patch(
        f"/api/v1/platform/station-flags/{uuid.uuid4()}",
        json={"status": "resolved"},
        headers=bearer(root),
    )
    assert response.status_code == 404
    assert response.json()["code"] == "station_flag_not_found"


async def test_a_library_station_can_be_reported_by_a_learner_with_no_org(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """Whose case it is does not matter: a reader inside nobody's institution
    can still find one wrong, and refusing them is how a bad case survives."""
    root = await make_actor(f"queue-{uuid.uuid4().hex[:8]}@osceguide.com", platform_admin=True)
    await create_exam(client, root, code="sca")
    library = await client.post(
        "/api/v1/platform/stations",
        json={"title": "A sore ankle", "exam_code": "sca", "content": CONTENT},
        headers=bearer(root),
    )
    learner = await make_actor("solo-learner@example.com")

    reported = await client.post(
        "/api/v1/me/station-flags",
        json={"station_id": library.json()["id"]},
        headers=bearer(learner),
    )
    assert reported.status_code == 204, reported.text

    assert (await client.get("/api/v1/me/station-flags", headers=bearer(learner))).json()["items"][0][
        "station_title"
    ] == "A sore ankle"
