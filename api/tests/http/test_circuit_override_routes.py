"""Every override, over HTTP, and who is allowed to press it.

The access matrix is the point of this file. Every route that ran an
examination used to take `may_read_org`, which admits trainees — so the
candidate sitting the circuit could start it, move it and end it. That is the
kind of hole a test exists to keep closed.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.features.voice.service import get_room_agents
from tests.http.test_sittings_routes import a_template_version
from tests.support.fakes import FakeRoomAgents
from tests.support.sittings import a_trainee, org_with_admin, published_station
from tests.support.tokens import bearer, mint_token

pytestmark = pytest.mark.db

# Every route that acts on a live examination, with a body that will pass
# validation. `{slot}` is filled in per test.
OVERRIDES = [
    ("advance", {}),
    ("pause", {}),
    ("extend-clock", {"seconds": 60}),
    ("reset-clock", {}),
    ("resend-patient", {}),
    ("redo-station", {"slot_id": "{slot}"}),
    ("jump-to", {"slot_id": "{slot}"}),
]


@pytest.fixture
def agents(client: AsyncClient) -> FakeRoomAgents:
    fake = FakeRoomAgents()
    client._transport.app.dependency_overrides[get_room_agents] = lambda: fake  # type: ignore[attr-defined]
    return fake


async def a_running_circuit(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,  # type: ignore[no-untyped-def]
) -> tuple[uuid.UUID, str, str, str, uuid.UUID]:
    org_id, admin = await org_with_admin(client, make_actor)
    template = await a_template_version(client, admin)
    sitting = (
        await client.post(
            "/api/v1/orgs/kings/sittings",
            json={"name": "S", "programme_id": str(template), "mode": "exam"},
            headers=bearer(admin),
        )
    ).json()
    versions = [await published_station(client, admin, "kings", f"S{i}") for i in range(2)]
    trainee_id = await a_trainee(db_session, f"o-{uuid.uuid4().hex[:8]}@example.com")
    circuit = (
        await client.post(
            f"/api/v1/orgs/kings/sittings/{sitting['id']}/circuits",
            json={
                "name": "C",
                "trainee_ids": [str(trainee_id)],
                "station_version_ids": versions,
            },
            headers=bearer(admin),
        )
    ).json()
    await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))
    return org_id, admin, circuit["id"], circuit["slots"][0]["id"], trainee_id


@pytest.mark.parametrize(("action", "body"), OVERRIDES)
async def test_an_admin_may_run_the_examination(
    client: AsyncClient,
    make_actor,  # type: ignore[no-untyped-def]
    db_session: AsyncSession,
    agents: FakeRoomAgents,
    action: str,
    body: dict[str, object],
) -> None:
    _, admin, circuit_id, slot_id, _ = await a_running_circuit(client, make_actor, db_session)
    if action == "resend-patient":
        # There has to be a station in progress to send a patient back into.
        await client.post(f"/api/v1/orgs/kings/circuits/{circuit_id}/advance", json={}, headers=bearer(admin))

    response = await client.post(
        f"/api/v1/orgs/kings/circuits/{circuit_id}/{action}",
        json={k: (slot_id if v == "{slot}" else v) for k, v in body.items()},
        headers=bearer(admin),
    )

    assert response.status_code == 200, response.text


@pytest.mark.parametrize(("action", "body"), OVERRIDES)
async def test_the_candidate_sitting_the_circuit_may_not_override_it(
    client: AsyncClient,
    make_actor,  # type: ignore[no-untyped-def]
    db_session: AsyncSession,
    agents: FakeRoomAgents,
    action: str,
    body: dict[str, object],
) -> None:
    """The hole this closes: `may_read_org` includes `trainee`.

    The candidate is given a real membership of the organisation, so this is
    the run policy refusing rather than the caller simply not being a member.
    """
    from app.features.tenancy import repository as tenancy_repository

    org_id, _, circuit_id, slot_id, trainee_id = await a_running_circuit(client, make_actor, db_session)
    await tenancy_repository.add_membership(
        db_session, org_id=org_id, user_id=trainee_id, role="trainee", product_surface=None
    )
    await db_session.flush()
    as_trainee = mint_token(
        user_id=trainee_id,
        email=f"sitting-{uuid.uuid4().hex[:6]}@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="trainee"),),
        active_org_slug="kings",
    )

    response = await client.post(
        f"/api/v1/orgs/kings/circuits/{circuit_id}/{action}",
        json={k: (slot_id if v == "{slot}" else v) for k, v in body.items()},
        headers=bearer(as_trainee),
    )

    assert response.status_code == 403


async def test_a_supervisor_may_run_the_examination(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    """ "Examiner" is a label for this role, not a role of its own."""
    org_id, _, circuit_id, _, _ = await a_running_circuit(client, make_actor, db_session)
    supervisor = await make_actor(
        f"sup-{uuid.uuid4().hex[:6]}@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="supervisor"),),
        active_org_slug="kings",
    )

    response = await client.post(
        f"/api/v1/orgs/kings/circuits/{circuit_id}/pause", json={}, headers=bearer(supervisor)
    )

    assert response.status_code == 200, response.text


async def test_an_override_names_who_did_it_and_why(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    _, admin, circuit_id, _, _ = await a_running_circuit(client, make_actor, db_session)

    await client.post(
        f"/api/v1/orgs/kings/circuits/{circuit_id}/extend-clock",
        json={"seconds": 300, "reason": "the projector failed"},
        headers=bearer(admin),
    )
    response = await client.get(
        f"/api/v1/orgs/kings/circuits/{circuit_id}/interventions", headers=bearer(admin)
    )

    assert response.status_code == 200, response.text
    [entry] = response.json()["items"]
    assert entry["action"] == "extend_clock"
    assert entry["reason"] == "the projector failed"
    assert entry["actor_user_id"] is not None


async def test_an_absurd_extension_is_refused_before_it_reaches_the_clock(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    """A mistyped value must not strand a circuit until the reaper finds it."""
    _, admin, circuit_id, _, _ = await a_running_circuit(client, make_actor, db_session)

    response = await client.post(
        f"/api/v1/orgs/kings/circuits/{circuit_id}/extend-clock",
        json={"seconds": 99999},
        headers=bearer(admin),
    )

    assert response.status_code == 422


async def test_handing_a_training_circuit_back_to_its_tutor(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    """Training runs on the same clock; this is the switch that stops it.

    A tutor who wants to talk between stations turns it off, and the circuit
    waits for them rather than moving the group on mid-sentence.
    """
    _, admin, circuit_id, _, _ = await a_running_circuit(client, make_actor, db_session)

    response = await client.patch(
        f"/api/v1/orgs/kings/circuits/{circuit_id}/auto-advance",
        json={"enabled": False},
        headers=bearer(admin),
    )

    assert response.status_code == 200, response.text
    assert response.json()["auto_advance"] is False
