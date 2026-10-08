"""Putting a latecomer at a station, rather than at whichever one comes first.

Oracle: `b2b-api/app/features/sessions/circuit_service.py::append_trainees_to_circuit`
behind `POST /orgs/{org}/sessions/{id}/circuits/{id}/append-trainees`, whose body
was `{entries: [{traineeId, stationRef}]}` — every arrival carried its own
station — and whose dialog said "Choose the station for this turn, library, your
organisation, or one already on this circuit"
(`frontend/src/b2b/components/features/sessions/live-runner/components/LiveCircuitAddTraineeModal.tsx`).
This route took `trainee_ids` alone and put everyone on the first slot's station,
which is wrong for the case the dialog was built for: a training circuit pairs
each person with a *position*, so three latecomers belong at three stations.

Two refusals are ported from the same function: it answered an arrival already on
the circuit with 409 rather than letting the unique index answer with a 500, and
it checked the station before writing.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.voice.service import get_room_agents
from tests.http.test_sittings_routes import (
    a_template_version,
    a_trainee,
    published_station,
)
from tests.support.fakes import FakeRoomAgents
from tests.support.sittings import org_with_admin
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


@pytest.fixture
def agents(client: AsyncClient) -> FakeRoomAgents:
    """A patient that never reaches LiveKit. Starting a circuit touches the room."""
    fake = FakeRoomAgents()
    client._transport.app.dependency_overrides[get_room_agents] = lambda: fake  # type: ignore[attr-defined]
    return fake


async def a_running_training_circuit(
    client: AsyncClient, db_session: AsyncSession, admin: str, *, people: int = 2
) -> tuple[dict, list[str]]:  # type: ignore[type-arg]
    """A training circuit of `people` at `people` stations, already started.

    Started, because that is the only moment appending is interesting: a circuit
    nobody has begun is corrected by rebuilding it.
    """
    template = await a_template_version(client, admin)
    sitting = (
        await client.post(
            "/api/v1/orgs/kings/sittings",
            json={"name": "Practice afternoon", "programme_id": str(template), "mode": "training"},
            headers=bearer(admin),
        )
    ).json()
    stations = [
        await published_station(client, admin, "kings", f"Station {index}") for index in range(1, people + 1)
    ]
    trainees = [str(await a_trainee(db_session, f"on{index}@example.com")) for index in range(people)]
    circuit = (
        await client.post(
            f"/api/v1/orgs/kings/sittings/{sitting['id']}/circuits",
            json={"name": "Room 1", "trainee_ids": trainees, "station_version_ids": stations},
            headers=bearer(admin),
        )
    ).json()
    started = await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))
    assert started.status_code == 200, started.text
    return circuit, stations


async def append(
    client: AsyncClient,
    admin: str,
    circuit_id: str,
    *,
    trainee_ids: list[str],
    station_version_ids: list[str] | None = None,
):  # type: ignore[no-untyped-def]
    body: dict = {"trainee_ids": trainee_ids}  # type: ignore[assignment]
    if station_version_ids is not None:
        body["station_version_ids"] = station_version_ids
    return await client.post(
        f"/api/v1/orgs/kings/circuits/{circuit_id}/append-trainees", json=body, headers=bearer(admin)
    )


async def test_appended_trainees_take_their_own_stations(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    """Two arrivals, two stations, named in the order they are to be placed."""
    _, admin = await org_with_admin(client, make_actor)
    circuit, stations = await a_running_training_circuit(client, db_session, admin)
    first = await a_trainee(db_session, "early@example.com")
    second = await a_trainee(db_session, "later@example.com")

    response = await append(
        client,
        admin,
        circuit["id"],
        trainee_ids=[str(first), str(second)],
        station_version_ids=[stations[1], stations[0]],
    )

    assert response.status_code == 200, response.text
    slots = response.json()["slots"]
    assert len(slots) == 4, "two already, two appended"
    placed = {slot["trainee_id"]: slot["station_version_id"] for slot in slots}
    assert placed[str(first)] == stations[1]
    assert placed[str(second)] == stations[0]


async def test_an_appended_trainee_still_inherits_the_live_room(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    """Naming a station must not cost the latecomer the room (C8)."""
    _, admin = await org_with_admin(client, make_actor)
    circuit, stations = await a_running_training_circuit(client, db_session, admin)
    latecomer = await a_trainee(db_session, "knoocker@example.com")

    slots = (
        await append(
            client,
            admin,
            circuit["id"],
            trainee_ids=[str(latecomer)],
            station_version_ids=[stations[1]],
        )
    ).json()["slots"]

    added = next(slot for slot in slots if slot["trainee_id"] == str(latecomer))
    seated = next(slot for slot in slots if slot["id"] == circuit["slots"][0]["id"])
    assert added["room_name"] == seated["room_name"]


async def test_no_station_named_still_puts_them_where_the_circuit_is(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    """The behaviour the dialog's simplest case relies on, and the old contract.

    The circuit is on its first station, so that is where a latecomer with nobody
    to place them goes — the one body shape this route has always accepted.
    """
    _, admin = await org_with_admin(client, make_actor)
    circuit, stations = await a_running_training_circuit(client, db_session, admin)
    latecomer = await a_trainee(db_session, "quiet@example.com")

    slots = (await append(client, admin, circuit["id"], trainee_ids=[str(latecomer)])).json()["slots"]

    added = next(slot for slot in slots if slot["trainee_id"] == str(latecomer))
    assert added["station_version_id"] == circuit["slots"][0]["station_version_id"]


async def test_somebody_already_on_the_circuit_is_refused_not_written(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    """b2b's 409. Here the same attempt reached the unique index and came back 500."""
    _, admin = await org_with_admin(client, make_actor)
    circuit, _ = await a_running_training_circuit(client, db_session, admin)
    already = circuit["slots"][0]["trainee_id"]

    response = await append(client, admin, circuit["id"], trainee_ids=[already])

    assert response.status_code == 409, response.text
    assert response.json()["code"] == "trainee_already_on_circuit"


async def test_a_station_the_circuit_does_not_run_is_refused(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    """Narrower than b2b, which let any of the organisation's stations in.

    A station nobody on this circuit is sitting is not where a latecomer belongs:
    naming one changes what the circuit *is*, and that is the structural edit,
    which is refused for its own reasons once anything has been run.
    """
    _, admin = await org_with_admin(client, make_actor)
    circuit, _ = await a_running_training_circuit(client, db_session, admin)
    elsewhere = await published_station(client, admin, "kings", "A station nobody is at")
    latecomer = await a_trainee(db_session, "misplaced@example.com")

    response = await append(
        client,
        admin,
        circuit["id"],
        trainee_ids=[str(latecomer)],
        station_version_ids=[elsewhere],
    )

    assert response.status_code == 409, response.text
    assert response.json()["code"] == "station_not_on_circuit"


async def test_two_arrivals_and_one_station_is_refused_not_guessed(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    """A short station list read as "repeat the last" would crowd two people into one room."""
    _, admin = await org_with_admin(client, make_actor)
    circuit, stations = await a_running_training_circuit(client, db_session, admin)
    first = await a_trainee(db_session, "one@example.com")
    second = await a_trainee(db_session, "two@example.com")

    response = await append(
        client,
        admin,
        circuit["id"],
        trainee_ids=[str(first), str(second)],
        station_version_ids=[stations[0]],
    )

    assert response.status_code == 409, response.text
    assert response.json()["code"] == "invalid_circuit"


async def test_an_exam_circuit_still_refuses_a_second_candidate(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    """The rule is b2b's own, and the reason is the aggregate, not the mode.

    An exam circuit is one candidate through every station: a second person on it
    would share one room, one clock and one recording, and the transcript of that
    would then be marked as though a single doctor had produced it. b2b answered
    "Use Edit circuit for exam sessions"; what this backend points at instead is
    the thing that is actually equivalent — another circuit on the same sitting.
    """
    _, admin = await org_with_admin(client, make_actor)
    template = await a_template_version(client, admin)
    sitting = (
        await client.post(
            "/api/v1/orgs/kings/sittings",
            json={"name": "Finals", "programme_id": str(template), "mode": "exam"},
            headers=bearer(admin),
        )
    ).json()
    station = await published_station(client, admin, "kings", "Sore ankle")
    circuit = (
        await client.post(
            f"/api/v1/orgs/kings/sittings/{sitting['id']}/circuits",
            json={
                "name": "Candidate A",
                "trainee_ids": [str(await a_trainee(db_session, "solo@example.com"))],
                "station_version_ids": [station],
            },
            headers=bearer(admin),
        )
    ).json()
    late = await a_trainee(db_session, "arriving-late@example.com")

    # The way that does exist is asked for first, and the order matters: a
    # refusal rolls the session back, and an account created a moment earlier by
    # the fixture goes with it.
    their_own = await client.post(
        f"/api/v1/orgs/kings/sittings/{sitting['id']}/circuits",
        json={"name": "Candidate B", "trainee_ids": [str(late)], "station_version_ids": [station]},
        headers=bearer(admin),
    )
    refused = await append(client, admin, circuit["id"], trainee_ids=[str(late)])

    assert their_own.status_code == 201, their_own.text
    assert uuid.UUID(their_own.json()["slots"][0]["trainee_id"]) == late
    assert refused.status_code == 409, refused.text
    assert refused.json()["code"] == "not_permitted_in_mode"
