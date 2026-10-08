"""The exam-day board: what is happening in this building, this morning.

The screen that did not exist. A course lead could open one circuit's console,
or a list of sittings that did not say which were live, so "how is the morning
going" was answered by walking between rooms.

Every number is computed server-side. This is the screen somebody makes
decisions from, and a browser with a wrong system clock should not be one of
the inputs.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.core.ports import get_clock
from app.features.voice.service import get_room_agents
from tests.http.test_sittings_routes import (
    a_template_version,
    a_trainee,
    org_with_admin,
    published_station,
)
from tests.support.fakes import FakeClock, FakeRoomAgents
from tests.support.tokens import bearer, mint_token

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 18, 9, 0, tzinfo=UTC)


@pytest.fixture
def clock(client: AsyncClient) -> FakeClock:
    """A clock the test moves, so "how long is left" is a fact and not a race."""
    fake = FakeClock(NOW)
    app = client._transport.app  # type: ignore[attr-defined]
    app.dependency_overrides[get_clock] = lambda: fake
    app.dependency_overrides[get_room_agents] = lambda: FakeRoomAgents()
    return fake


async def a_running_morning(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    *,
    stations: int = 2,  # type: ignore[no-untyped-def]
) -> tuple[str, str, uuid.UUID]:
    org_id, admin = await org_with_admin(client, make_actor)
    template = await a_template_version(client, admin)
    sitting = (
        await client.post(
            "/api/v1/orgs/kings/sittings",
            json={"name": "Finals", "programme_id": str(template), "mode": "exam"},
            headers=bearer(admin),
        )
    ).json()
    versions = [await published_station(client, admin, "kings", f"Station {i}") for i in range(stations)]
    trainee_id = await a_trainee(db_session, f"p-{uuid.uuid4().hex[:8]}@example.com")
    circuit = (
        await client.post(
            f"/api/v1/orgs/kings/sittings/{sitting['id']}/circuits",
            json={
                "name": "Circuit A",
                "trainee_ids": [str(trainee_id)],
                "station_version_ids": versions,
            },
            headers=bearer(admin),
        )
    ).json()
    await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))
    return admin, circuit["id"], trainee_id


async def test_the_board_lists_every_running_circuit_with_its_clock(
    client: AsyncClient, make_actor, db_session: AsyncSession, clock: FakeClock
) -> None:  # type: ignore[no-untyped-def]
    admin, circuit_id, _ = await a_running_morning(client, make_actor, db_session)

    response = await client.get("/api/v1/orgs/kings/live", headers=bearer(admin))

    assert response.status_code == 200, response.text
    board = response.json()
    assert len(board["circuits"]) == 1
    row = board["circuits"][0]
    assert row["circuit_id"] == circuit_id
    assert row["sitting_name"] == "Finals"
    assert row["phase"] == "reading"
    assert row["stations_total"] == 2
    assert row["stations_completed"] == 0
    assert row["current_station"]["title"] == "Station 0"
    assert len(row["candidates"]) == 1


async def test_time_left_is_counted_against_the_servers_clock(
    client: AsyncClient, make_actor, db_session: AsyncSession, clock: FakeClock
) -> None:
    """Not the browser's. This is the screen decisions are made from."""
    admin, _, _ = await a_running_morning(client, make_actor, db_session)

    clock.set(NOW + timedelta(minutes=1))
    response = await client.get("/api/v1/orgs/kings/live", headers=bearer(admin))

    row = response.json()["circuits"][0]
    assert row["remaining_seconds"] == 120, "three minutes of reading, one gone"
    assert row["elapsed_seconds"] == 60


async def test_a_paused_circuit_stops_counting_down(
    client: AsyncClient, make_actor, db_session: AsyncSession, clock: FakeClock
) -> None:
    """A paused examination that visibly ran out would be alarming and wrong."""
    admin, circuit_id, _ = await a_running_morning(client, make_actor, db_session)
    clock.set(NOW + timedelta(minutes=1))
    await client.post(f"/api/v1/orgs/kings/circuits/{circuit_id}/pause", json={}, headers=bearer(admin))

    clock.set(NOW + timedelta(hours=1))
    response = await client.get("/api/v1/orgs/kings/live", headers=bearer(admin))

    row = response.json()["circuits"][0]
    assert row["paused"] is True
    assert row["remaining_seconds"] == 120, "frozen where the clock stopped"
    assert row["alerts"] == [], "a stopped clock is not an overdue one"


async def test_a_consultation_with_nothing_recording_it_raises_an_alert(
    client: AsyncClient, make_actor, db_session: AsyncSession, clock: FakeClock
) -> None:
    """The failure this board exists for.

    The dispatch succeeded and no patient arrived. A supervisor used to find
    out by watching a silent room; now the morning's screen says so.
    """
    admin, circuit_id, _ = await a_running_morning(client, make_actor, db_session)
    await client.post(f"/api/v1/orgs/kings/circuits/{circuit_id}/advance", json={}, headers=bearer(admin))

    clock.set(NOW + timedelta(minutes=2))
    response = await client.get("/api/v1/orgs/kings/live", headers=bearer(admin))

    row = response.json()["circuits"][0]
    assert row["phase"] == "simulation"
    assert row["attempt_id"] is not None, "the recording exists"
    assert "no_running_attempt" in row["alerts"], "but the worker never bootstrapped it"


async def test_a_voice_fault_on_an_overdue_phase_says_voice_not_worker(
    client: AsyncClient, make_actor, db_session: AsyncSession, clock: FakeClock
) -> None:
    """R-16: the read tries to bring the patient in; LiveKit is not configured here, so it cannot.

    The board then names the voice service rather than a late clock, which would send
    somebody to look at the worker.
    """
    admin, _, _ = await a_running_morning(client, make_actor, db_session)

    clock.set(NOW + timedelta(minutes=10))
    response = await client.get("/api/v1/orgs/kings/live", headers=bearer(admin))

    row = response.json()["circuits"][0]
    assert row["phase"] == "reading"
    assert row["alerts"] == ["voice_fault"]


async def test_a_circuit_that_has_ended_leaves_the_board(
    client: AsyncClient, make_actor, db_session: AsyncSession, clock: FakeClock
) -> None:
    admin, circuit_id, _ = await a_running_morning(client, make_actor, db_session)
    await client.post(f"/api/v1/orgs/kings/circuits/{circuit_id}/end", headers=bearer(admin))

    response = await client.get("/api/v1/orgs/kings/live", headers=bearer(admin))

    assert response.json()["circuits"] == []


async def test_a_candidate_cannot_read_the_board(
    client: AsyncClient, make_actor, db_session: AsyncSession, clock: FakeClock
) -> None:
    """It names every candidate and how each is doing.

    That is not a thing a candidate may read about the people sitting beside
    them, and `may_read_org` — which every run route used to take — would have
    let them.
    """
    from app.features.tenancy import repository as tenancy_repository

    _, _, trainee_id = await a_running_morning(client, make_actor, db_session)
    org = await tenancy_repository.organization_by_slug(db_session, "kings")
    assert org is not None
    await tenancy_repository.add_membership(
        db_session, org_id=org.id, user_id=trainee_id, role="trainee", product_surface=None
    )
    await db_session.flush()
    as_trainee = mint_token(
        user_id=trainee_id,
        email="board-trainee@example.com",
        memberships=(Membership(org_id=org.id, org_slug="kings", role="trainee"),),
        active_org_slug="kings",
    )

    response = await client.get("/api/v1/orgs/kings/live", headers=bearer(as_trainee))

    assert response.status_code == 403


async def test_a_supervisor_can_read_the_board(
    client: AsyncClient, make_actor, db_session: AsyncSession, clock: FakeClock
) -> None:
    """They are the person running the morning."""
    from app.features.tenancy import repository as tenancy_repository

    await a_running_morning(client, make_actor, db_session)
    org = await tenancy_repository.organization_by_slug(db_session, "kings")
    assert org is not None
    supervisor = await make_actor(
        "supervisor@example.com",
        memberships=(Membership(org_id=org.id, org_slug="kings", role="supervisor"),),
        active_org_slug="kings",
    )

    response = await client.get("/api/v1/orgs/kings/live", headers=bearer(supervisor))

    assert response.status_code == 200
    assert len(response.json()["circuits"]) == 1


async def test_a_circuit_that_has_ended_is_kept_in_the_boards_history(
    client: AsyncClient, make_actor, db_session: AsyncSession, clock: FakeClock
) -> None:
    """Gone from the live board, and still there to look back at.

    Ended before any station was sat, so it is filed as `ended_early` with
    nothing completed — the unsat stations are skipped, not counted.
    """
    admin, circuit_id, _ = await a_running_morning(client, make_actor, db_session)
    assert (await client.get("/api/v1/orgs/kings/live/history", headers=bearer(admin))).json()["items"] == []

    clock.advance(7 * 60)
    ended = await client.post(f"/api/v1/orgs/kings/circuits/{circuit_id}/end", headers=bearer(admin))
    assert ended.status_code == 200, ended.text

    response = await client.get("/api/v1/orgs/kings/live/history", headers=bearer(admin))
    assert response.status_code == 200, response.text
    assert response.json()["next_cursor"] is None
    (run,) = response.json()["items"]
    assert run["circuit_id"] == circuit_id
    assert run["circuit_name"] == "Circuit A"
    assert run["sitting_name"] == "Finals"
    assert run["mode"] == "exam"
    assert run["started_at"] == "2026-09-18T09:00:00Z"
    assert run["ended_at"] == "2026-09-18T09:07:00Z"
    assert run["candidate_count"] == 1
    assert (run["stations_total"], run["stations_completed"]) == (2, 0)
    assert run["status"] == "ended_early"

    # Ending it again is a no-op, not a second run.
    await client.post(f"/api/v1/orgs/kings/circuits/{circuit_id}/end", headers=bearer(admin))
    again = await client.get("/api/v1/orgs/kings/live/history", headers=bearer(admin))
    assert len(again.json()["items"]) == 1


async def test_a_candidate_cannot_read_the_boards_history(
    client: AsyncClient, make_actor, db_session: AsyncSession, clock: FakeClock
) -> None:
    from app.features.tenancy import repository as tenancy_repository

    await a_running_morning(client, make_actor, db_session)
    org = await tenancy_repository.organization_by_slug(db_session, "kings")
    assert org is not None
    candidate = await make_actor(
        "history-trainee@example.com",
        memberships=(Membership(org_id=org.id, org_slug="kings", role="trainee"),),
        active_org_slug="kings",
    )
    response = await client.get("/api/v1/orgs/kings/live/history", headers=bearer(candidate))
    assert response.status_code == 403


def test_a_run_is_complete_only_when_every_station_was_sat() -> None:
    from app.features.sittings.domain_run import run_status

    assert run_status(stations_total=3, stations_completed=3) == "completed"
    assert run_status(stations_total=3, stations_completed=2) == "ended_early"
    assert run_status(stations_total=0, stations_completed=0) == "ended_early"


async def test_reading_the_board_advances_a_circuit_the_worker_left_behind(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    clock: FakeClock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """S-7: the worker is down, so the read moves the circuit on, once, and says the worker is down."""
    from app.features.sittings import service_run

    monkeypatch.setattr(service_run, "get_room_agents", lambda: FakeRoomAgents())
    admin, _, _ = await a_running_morning(client, make_actor, db_session)

    clock.set(NOW + timedelta(minutes=10))
    first = (await client.get("/api/v1/orgs/kings/live", headers=bearer(admin))).json()
    second = (await client.get("/api/v1/orgs/kings/live", headers=bearer(admin))).json()

    row = first["circuits"][0]
    assert row["phase"] == "simulation"
    assert row["remaining_seconds"] == 600
    assert "clock_overdue" not in row["alerts"]
    assert second["circuits"][0]["phase"] == "simulation", "a second read must not advance it again"
    assert second["circuits"][0]["remaining_seconds"] == 600
    assert first["worker_running"] is False, "no worker has checked in"


async def test_a_fresh_worker_heartbeat_means_the_worker_is_running(
    client: AsyncClient, make_actor, db_session: AsyncSession, clock: FakeClock
) -> None:
    from sqlalchemy import text

    admin, _, _ = await a_running_morning(client, make_actor, db_session)
    await db_session.execute(text("INSERT INTO procrastinate_workers DEFAULT VALUES"))

    board = (await client.get("/api/v1/orgs/kings/live", headers=bearer(admin))).json()

    assert board["worker_running"] is True
