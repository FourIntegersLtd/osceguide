"""Read-model additions the institution screens need: counts on the sittings read, invited-not-joined,
overdue seconds, the exam's break default and the exam id on a reporting row."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import event, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.sittings.models import Circuit
from tests.http.test_org_read_models import a_circuit, a_user
from tests.support.sittings import a_sitting, add_programme, org_with_admin, published_station
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def _two_circuits(client: AsyncClient, make_actor, db_session: AsyncSession):  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings", mode="training")
    stations = [
        await published_station(client, admin, "kings", "S1"),
        await published_station(client, admin, "kings", "S2"),
    ]
    ada = await a_user(db_session, "ada@example.com")
    ben = await a_user(db_session, "ben@example.com")
    cat = await a_user(db_session, "cat@example.com")
    for ids in ([ada, ben], [ben, cat]):
        await a_circuit(
            client,
            admin,
            "kings",
            sitting_id=sitting["id"],
            trainee_ids=[str(i) for i in ids],
            station_version_ids=stations,
        )
    return org_id, admin, sitting


async def test_the_sittings_list_and_home_count_circuits_and_candidates(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _, admin, sitting = await _two_circuits(client, make_actor, db_session)
    empty = await client.post(
        "/api/v1/orgs/kings/sittings",
        json={"name": "Later", "programme_id": sitting["programme_id"], "mode": "training"},
        headers=bearer(admin),
    )
    assert empty.status_code == 201, empty.text

    listed = await client.get("/api/v1/orgs/kings/sittings", headers=bearer(admin))
    by_name = {s["name"]: (s["circuit_count"], s["candidate_count"]) for s in listed.json()["items"]}
    # Ben sits on both circuits and is counted once.
    assert by_name == {"Finals": (2, 3), "Later": (0, 0)}

    home = await client.get("/api/v1/orgs/kings/dashboard", headers=bearer(admin))
    rows = {s["name"]: (s["circuit_count"], s["candidate_count"]) for s in home.json()["recent_sittings"]}
    assert rows == by_name


async def test_the_sittings_list_counts_in_a_fixed_number_of_queries(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _, admin, sitting = await _two_circuits(client, make_actor, db_session)
    seen: list[str] = []
    engine = db_session.bind.sync_engine  # type: ignore[union-attr]

    def count(conn, cursor, statement, *args):  # type: ignore[no-untyped-def]
        seen.append(statement)

    async def statements() -> int:
        seen.clear()
        response = await client.get("/api/v1/orgs/kings/sittings", headers=bearer(admin))
        assert response.status_code == 200
        return len(seen)

    event.listen(engine, "before_cursor_execute", count)
    try:
        before = await statements()
        for n in range(3):
            await client.post(
                "/api/v1/orgs/kings/sittings",
                json={"name": f"More {n}", "programme_id": sitting["programme_id"], "mode": "training"},
                headers=bearer(admin),
            )
        after = await statements()
    finally:
        event.remove(engine, "before_cursor_execute", count)
    assert after == before


async def test_the_home_counts_trainees_who_have_not_joined(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from app.features.identity import repository as identity_repo
    from app.features.roster import repository as roster_repo

    org_id, admin = await org_with_admin(client, make_actor)
    await a_user(db_session, "pending1@example.com")
    await a_user(db_session, "pending2@example.com")
    joined = await identity_repo.create_user(
        session=db_session, email="joined@example.com", name="J", password_hash="x"
    )
    await db_session.flush()
    trainee = await roster_repo.create_trainee(
        db_session, org_id, email="joined@example.com", first_name=None, last_name=None, cohort_id=None
    )
    await roster_repo.link_trainee_to_user(db_session, org_id, trainee.id, user_id=joined.id)
    await db_session.flush()

    body = (await client.get("/api/v1/orgs/kings/dashboard", headers=bearer(admin))).json()
    assert body["counts"]["trainees"] == 3
    assert body["counts"]["invited_not_joined"] == 2


async def test_an_overdue_circuit_says_by_how_many_seconds(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _, admin, sitting = await _two_circuits(client, make_actor, db_session)
    detail = await client.get(f"/api/v1/orgs/kings/sittings/{sitting['id']}", headers=bearer(admin))
    circuit_id = detail.json()["circuits"][0]["id"]
    await client.post(f"/api/v1/orgs/kings/circuits/{circuit_id}/start", headers=bearer(admin))
    await db_session.execute(
        update(Circuit)
        .where(Circuit.id == circuit_id)
        .values(phase_ends_at=datetime.now(UTC) - timedelta(seconds=90))
    )
    await db_session.flush()

    response = await client.get(f"/api/v1/orgs/kings/circuits/{circuit_id}/console", headers=bearer(admin))
    console = response.json()
    assert 88 <= console["circuit"]["overdue_seconds"] <= 120


async def test_an_exam_carries_a_default_break_into_its_programme(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _, admin, _ = await _two_circuits(client, make_actor, db_session)
    programmes = (await client.get("/api/v1/orgs/kings/programmes", headers=bearer(admin))).json()["items"]
    assert programmes[0]["default_break_minutes"] is None
    assert programmes[0]["default_reading_seconds"] > 0

    from tests.http.test_org_authored_exams import author_exam

    exam = await author_exam(client, admin, "kings", code="brk", publish=False)
    set_break = await client.patch(
        f"/api/v1/orgs/kings/exams/{exam['id']}",
        json={"settings": {"default_break_minutes": 7}},
        headers=bearer(admin),
    )
    assert set_break.status_code == 200, set_break.text
    assert set_break.json()["settings"]["default_break_minutes"] == 7
    published = await client.post(f"/api/v1/orgs/kings/exams/{exam['id']}/publish", headers=bearer(admin))
    assert published.status_code == 200, published.text
    await add_programme(client, admin, org_slug="kings", exam_code="brk")
    rows = (await client.get("/api/v1/orgs/kings/programmes", headers=bearer(admin))).json()["items"]
    mine = next(row for row in rows if row["exam_code"] == "brk")
    assert (mine["default_break_minutes"], mine["default_reading_seconds"]) == (7, 120)

    refused = await client.patch(
        f"/api/v1/orgs/kings/exams/{exam['id']}",
        json={"settings": {"default_break_minutes": 61}},
        headers=bearer(admin),
    )
    assert refused.status_code == 422


async def test_a_reporting_row_names_its_exam(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _, admin, _ = await _two_circuits(client, make_actor, db_session)
    rows = (await client.get("/api/v1/orgs/kings/reporting", headers=bearer(admin))).json()["programmes"]
    programmes = (await client.get("/api/v1/orgs/kings/programmes", headers=bearer(admin))).json()["items"]
    assert rows[0]["exam_id"] == programmes[0]["exam_id"]
