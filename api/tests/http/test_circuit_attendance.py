"""No-show and dropped-connection handling: who may, why it is required, and what it leaves behind."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.voice.service import get_room_agents
from tests.conftest import _test_session
from tests.http.test_circuit_override_routes import a_running_circuit
from tests.http.test_circuit_training_room import a_room, join
from tests.support.fakes import FakeRoomAgents, FakeVoiceTokens
from tests.support.tokens import bearer, mint_token

pytestmark = pytest.mark.db


@pytest.fixture
def agents(client: AsyncClient) -> FakeRoomAgents:
    fake = FakeRoomAgents()
    client._transport.app.dependency_overrides[get_room_agents] = lambda: fake  # type: ignore[attr-defined]
    return fake


def _url(circuit_id: str, tail: str) -> str:
    return f"/api/v1/orgs/kings/circuits/{circuit_id}/{tail}"


async def _interventions(client: AsyncClient, admin: str, circuit_id: str) -> list[dict[str, object]]:
    response = await client.get(_url(circuit_id, "interventions"), headers=bearer(admin))
    assert response.status_code == 200, response.text
    return response.json()["items"]


async def _candidate_leaves(db_session: AsyncSession, slot_id: str) -> None:
    """The worker ends the interaction when the candidate disconnects."""
    from datetime import UTC, datetime

    from app.features.attempts import repository as attempts_repo
    from app.features.attempts.domain import Status

    attempt = (await attempts_repo.live_attempts_for_slots(db_session, [uuid.UUID(slot_id)]))[0]
    now = datetime.now(UTC)
    if attempt.status == "created":
        await attempts_repo.set_status(db_session, attempt.id, status=Status.RUNNING, at=now)
    await attempts_repo.set_status(db_session, attempt.id, status=Status.INTERACTION_COMPLETE, at=now)
    _test_session().expire_all()


async def _my_sitting(client: AsyncClient, trainee_id: uuid.UUID, circuit_id: str) -> dict[str, object]:
    sittings = (
        await client.get("/api/v1/me/sittings", headers=bearer(mint_token(user_id=trainee_id)))
    ).json()["items"]
    return next(item for item in sittings if item["circuit_id"] == circuit_id)


async def test_marking_absent_requires_a_reason(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    _, admin, circuit_id, _, trainee_id = await a_running_circuit(client, make_actor, db_session)
    for body in ({"trainee_id": str(trainee_id)}, {"trainee_id": str(trainee_id), "reason": "  "}):
        response = await client.post(_url(circuit_id, "mark-absent"), json=body, headers=bearer(admin))
        assert response.status_code == 422


async def test_marking_absent_skips_stations_ends_the_circuit_and_is_recorded_twice(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    _, admin, circuit_id, _, trainee_id = await a_running_circuit(client, make_actor, db_session)

    response = await client.post(
        _url(circuit_id, "mark-absent"),
        json={"trainee_id": str(trainee_id), "reason": "Did not arrive by 09:30"},
        headers=bearer(admin),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert [slot["status"] for slot in body["slots"]] == ["skipped", "skipped"]
    assert body["ended_at"] is not None
    logged = await _interventions(client, admin, circuit_id)
    assert [(row["action"], row["reason"]) for row in logged] == [("mark_absent", "Did not arrive by 09:30")]
    audited = (
        (
            await db_session.execute(
                text("select summary from audit_log where action = 'circuit.candidate_marked_absent'")
            )
        )
        .scalars()
        .all()
    )
    assert len(audited) == 1 and "Did not arrive by 09:30" in audited[0]


async def test_marking_absent_twice_writes_one_record(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    _, admin, circuit_id, _, trainee_id = await a_running_circuit(client, make_actor, db_session)
    body = {"trainee_id": str(trainee_id), "reason": "No show"}
    # Ended by the first call, so the second is refused rather than repeated.
    assert (
        await client.post(_url(circuit_id, "mark-absent"), json=body, headers=bearer(admin))
    ).status_code == 200
    again = await client.post(_url(circuit_id, "mark-absent"), json=body, headers=bearer(admin))
    assert again.status_code == 409
    assert len(await _interventions(client, admin, circuit_id)) == 1


async def test_a_candidate_who_has_started_cannot_be_marked_absent(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    _, admin, circuit_id, _, trainee_id = await a_running_circuit(client, make_actor, db_session)
    await client.post(
        _url(circuit_id, "advance"), json={}, headers=bearer(admin)
    )  # patient in: station under way

    response = await client.post(
        _url(circuit_id, "mark-absent"),
        json={"trainee_id": str(trainee_id), "reason": "Gone"},
        headers=bearer(admin),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "candidate_already_sat"


async def test_the_portal_tells_a_candidate_marked_absent_they_cannot_join(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    _, admin, circuit_id, _, trainee_id = await a_running_circuit(client, make_actor, db_session)
    await client.post(
        _url(circuit_id, "mark-absent"),
        json={"trainee_id": str(trainee_id), "reason": "No show"},
        headers=bearer(admin),
    )
    token = mint_token(user_id=trainee_id)
    sittings = (await client.get("/api/v1/me/sittings", headers=bearer(token))).json()["items"]
    mine = next(item for item in sittings if item["circuit_id"] == circuit_id)
    assert mine["marked_absent"] is True
    assert mine["can_join"] is False


async def test_a_supervisor_in_another_org_cannot_mark_absent(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    _, _, circuit_id, _, trainee_id = await a_running_circuit(client, make_actor, db_session)
    outsider = mint_token(user_id=uuid.uuid4())
    response = await client.post(
        _url(circuit_id, "mark-absent"),
        json={"trainee_id": str(trainee_id), "reason": "x y z"},
        headers=bearer(outsider),
    )
    assert response.status_code in (401, 403, 404)


async def test_a_rejoin_needs_a_dropped_connection_and_a_reason_and_is_allowed_once(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    _, admin, circuit_id, slot_id, trainee_id = await a_running_circuit(client, make_actor, db_session)
    await client.post(_url(circuit_id, "advance"), json={}, headers=bearer(admin))  # simulation, patient in
    before = (await client.get(_url(circuit_id, "console"), headers=bearer(admin))).json()["circuit"]

    # The conversation is still running: nothing dropped.
    still = await client.post(
        _url(circuit_id, "allow-rejoin"), json={"reason": "Wifi dropped"}, headers=bearer(admin)
    )
    assert still.status_code == 409 and still.json()["code"] == "candidate_still_connected"

    no_reason = await client.post(_url(circuit_id, "allow-rejoin"), json={}, headers=bearer(admin))
    assert no_reason.status_code == 422

    # The worker ends the interaction when the candidate leaves.
    await _candidate_leaves(db_session, slot_id)
    assert (await _my_sitting(client, trainee_id, circuit_id))["waiting_for_rejoin"] is True
    allowed = await client.post(
        _url(circuit_id, "allow-rejoin"), json={"reason": "Wifi dropped"}, headers=bearer(admin)
    )
    assert allowed.status_code == 200, allowed.text
    after = (await client.get(_url(circuit_id, "console"), headers=bearer(admin))).json()["circuit"]
    assert after["phase_ends_at"] == before["phase_ends_at"]  # the server's clock was not touched

    await _candidate_leaves(db_session, slot_id)
    # The one re-join is spent: the candidate is no longer told a supervisor can let them back in.
    assert (await _my_sitting(client, trainee_id, circuit_id))["waiting_for_rejoin"] is False
    second = await client.post(
        _url(circuit_id, "allow-rejoin"), json={"reason": "Dropped again"}, headers=bearer(admin)
    )
    assert second.status_code == 409 and second.json()["code"] == "rejoin_already_used"

    logged = await _interventions(client, admin, circuit_id)
    assert [(r["action"], r["reason"]) for r in logged if r["action"] == "allow_rejoin"] == [
        ("allow_rejoin", "Wifi dropped")
    ]
    audited = (
        await db_session.execute(
            text("select count(*) from audit_log where action = 'circuit.rejoin_allowed'")
        )
    ).scalar_one()
    assert audited == 1


async def test_a_candidate_may_not_allow_their_own_rejoin(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    from app.features.tenancy import repository as tenancy_repository

    org_id, admin, circuit_id, _, trainee_id = await a_running_circuit(client, make_actor, db_session)
    await client.post(_url(circuit_id, "advance"), json={}, headers=bearer(admin))
    await tenancy_repository.add_membership(
        db_session, org_id=org_id, user_id=trainee_id, role="trainee", product_surface=None
    )
    await db_session.flush()
    token = mint_token(user_id=trainee_id)
    for tail, body in (
        ("allow-rejoin", {"reason": "mine"}),
        ("mark-absent", {"trainee_id": str(trainee_id), "reason": "mine"}),
    ):
        response = await client.post(_url(circuit_id, tail), json=body, headers=bearer(token))
        assert response.status_code == 403


async def test_a_trainee_marked_absent_is_refused_the_room_while_the_others_carry_on(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,
    voice_tokens: FakeVoiceTokens,  # type: ignore[no-untyped-def]
) -> None:
    room = await a_room(client, make_actor, db_session)

    response = await client.post(
        f"{room.base}/mark-absent",
        json={"trainee_id": str(room.trainees[1]), "reason": "Phoned in sick"},
        headers=bearer(room.admin),
    )

    assert response.status_code == 200, response.text
    assert response.json()["ended_at"] is None  # the other trainee is still being examined
    refused = await join(client, room, 1)
    assert refused.status_code == 409 and refused.json()["code"] == "candidate_marked_absent"
    assert (await join(client, room, 0)).status_code == 200


async def test_a_candidate_whose_circuit_was_ended_early_is_not_told_they_were_absent(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    _, admin, circuit_id, _, trainee_id = await a_running_circuit(client, make_actor, db_session)
    ended = await client.post(_url(circuit_id, "end"), json={"reason": "Fire alarm"}, headers=bearer(admin))
    assert ended.status_code == 200, ended.text
    mine = await _my_sitting(client, trainee_id, circuit_id)
    assert mine["marked_absent"] is False
