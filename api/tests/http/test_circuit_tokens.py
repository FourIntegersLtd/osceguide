"""Getting into the room: the candidate, and the examiner watching them.

Two tokens, and the difference between them is the whole point. A candidate
speaks and is recorded; an examiner hears the consultation and cannot be heard
in it. Enforced in the token, because a muted microphone is a UI state and this
has to be a guarantee.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.features.voice.service import get_room_agents, get_voice_tokens
from tests.http.test_sittings_routes import (
    a_template_version,
    a_trainee,
    org_with_admin,
    published_station,
)
from tests.support.fakes import FakeRoomAgents, FakeVoiceTokens
from tests.support.tokens import bearer, mint_token

pytestmark = pytest.mark.db


@pytest.fixture
def tokens(client: AsyncClient) -> FakeVoiceTokens:
    fake = FakeVoiceTokens()
    app = client._transport.app  # type: ignore[attr-defined]
    app.dependency_overrides[get_voice_tokens] = lambda: fake
    app.dependency_overrides[get_room_agents] = lambda: FakeRoomAgents()
    return fake


async def a_live_circuit(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,  # type: ignore[no-untyped-def]
    *,
    mode: str = "exam",
) -> tuple[str, str, str, uuid.UUID]:
    """An org admin, a started circuit, and the candidate rostered onto it."""
    org_id, admin = await org_with_admin(client, make_actor)
    template = await a_template_version(client, admin)
    sitting = (
        await client.post(
            "/api/v1/orgs/kings/sittings",
            json={"name": "S", "programme_id": str(template), "mode": mode},
            headers=bearer(admin),
        )
    ).json()
    station = await published_station(client, admin, "kings", "S1")
    trainee_id = await a_trainee(db_session, f"cand-{uuid.uuid4().hex[:8]}@example.com")
    circuit = (
        await client.post(
            f"/api/v1/orgs/kings/sittings/{sitting['id']}/circuits",
            json={"name": "C", "trainee_ids": [str(trainee_id)], "station_version_ids": [station]},
            headers=bearer(admin),
        )
    ).json()
    started = await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))
    assert started.status_code == 200, started.text
    # Minted for the trainee the roster already created, rather than through
    # `make_actor`, which makes a new person: the point of every assertion here
    # is that this is the identity the circuit knows.
    candidate = mint_token(user_id=trainee_id, email=f"c-{trainee_id}@example.com")
    return admin, candidate, circuit["id"], trainee_id


async def test_a_candidate_joins_the_room_with_no_patient_attached(
    client: AsyncClient, make_actor, db_session: AsyncSession, tokens: FakeVoiceTokens
) -> None:  # type: ignore[no-untyped-def]
    """The orchestrator brings the patient in, not the candidate's own token.

    The consumer path carries a dispatch on the candidate's token, because
    there is nobody else to do it. Doing that here would put a second patient
    in beside the one the circuit dispatched, and both would answer.
    """
    _, candidate, circuit_id, trainee_id = await a_live_circuit(client, make_actor, db_session)

    response = await client.post(f"/api/v1/me/circuits/{circuit_id}/join-token", headers=bearer(candidate))

    assert response.status_code == 200, response.text
    assert response.json()["room"] == f"circuit_{circuit_id}"
    granted = tokens.issued[-1]
    assert granted["agent_name"] is None
    assert granted["can_publish"] is True


async def test_a_candidates_identity_is_the_one_the_patient_waits_for(
    client: AsyncClient, make_actor, db_session: AsyncSession, tokens: FakeVoiceTokens
) -> None:
    """The worker is handed a `candidate_ref` and waits for exactly that identity.

    A different spelling here and the patient sits in the room waiting for
    somebody who, as far as LiveKit is concerned, never arrives.
    """
    _, candidate, circuit_id, trainee_id = await a_live_circuit(client, make_actor, db_session)

    await client.post(f"/api/v1/me/circuits/{circuit_id}/join-token", headers=bearer(candidate))

    assert tokens.issued[-1]["identity"] == str(trainee_id)


async def test_somebody_not_on_the_circuit_is_told_it_does_not_exist(
    client: AsyncClient, make_actor, db_session: AsyncSession, tokens: FakeVoiceTokens
) -> None:
    """404 rather than 403: whether a circuit exists is not something to
    confirm to somebody who is not on it."""
    _, _, circuit_id, _ = await a_live_circuit(client, make_actor, db_session)
    stranger = await make_actor("stranger@example.com")

    response = await client.post(f"/api/v1/me/circuits/{circuit_id}/join-token", headers=bearer(stranger))

    assert response.status_code == 404
    assert response.json()["code"] == "circuit_not_found"


async def test_there_is_no_room_before_the_circuit_starts(
    client: AsyncClient, make_actor, db_session: AsyncSession, tokens: FakeVoiceTokens
) -> None:
    org_id, admin = await org_with_admin(client, make_actor)
    template = await a_template_version(client, admin)
    sitting = (
        await client.post(
            "/api/v1/orgs/kings/sittings",
            json={"name": "S", "programme_id": str(template), "mode": "exam"},
            headers=bearer(admin),
        )
    ).json()
    station = await published_station(client, admin, "kings", "S1")
    trainee_id = await a_trainee(db_session, "early@example.com")
    circuit = (
        await client.post(
            f"/api/v1/orgs/kings/sittings/{sitting['id']}/circuits",
            json={"name": "C", "trainee_ids": [str(trainee_id)], "station_version_ids": [station]},
            headers=bearer(admin),
        )
    ).json()
    candidate = mint_token(user_id=trainee_id, email="early-actor@example.com")

    response = await client.post(f"/api/v1/me/circuits/{circuit['id']}/join-token", headers=bearer(candidate))

    assert response.status_code == 409
    assert response.json()["code"] == "circuit_not_live"


async def test_an_examiner_can_listen_and_cannot_be_heard(
    client: AsyncClient, make_actor, db_session: AsyncSession, tokens: FakeVoiceTokens
) -> None:
    """The guarantee the whole observer idea rests on.

    A candidate must not be able to be prompted, and the transcript must stay a
    record of what they said to the patient and nothing else.
    """
    admin, _, circuit_id, _ = await a_live_circuit(client, make_actor, db_session)

    response = await client.post(
        f"/api/v1/orgs/kings/circuits/{circuit_id}/observer-token", headers=bearer(admin)
    )

    assert response.status_code == 200, response.text
    granted = tokens.issued[-1]
    assert granted["can_publish"] is False
    assert granted["agent_name"] is None
    assert response.json()["can_publish"] is False


async def test_a_training_supervisor_may_demonstrate_on_camera(
    client: AsyncClient, make_actor, db_session: AsyncSession, tokens: FakeVoiceTokens
) -> None:
    """The one deliberate exception to the observer guarantee above.

    A training circuit carries no result a prompted answer could corrupt, so
    a supervisor may publish — matching the retiring client, which let them
    demonstrate on camera while a trainee practised. Exam mode above is
    unaffected: this is a per-sitting relaxation, not a change to the rule.
    """
    admin, _, circuit_id, _ = await a_live_circuit(client, make_actor, db_session, mode="training")

    response = await client.post(
        f"/api/v1/orgs/kings/circuits/{circuit_id}/observer-token", headers=bearer(admin)
    )

    assert response.status_code == 200, response.text
    granted = tokens.issued[-1]
    assert granted["can_publish"] is True
    assert response.json()["can_publish"] is True


async def test_an_examiners_identity_is_never_mistaken_for_a_patient(
    client: AsyncClient, make_actor, db_session: AsyncSession, tokens: FakeVoiceTokens
) -> None:
    """Stale patients are swept from a room by matching `agent-`.

    An examiner whose identity began with that prefix would be thrown out of
    the room every time a station started.
    """
    admin, _, circuit_id, _ = await a_live_circuit(client, make_actor, db_session)

    await client.post(f"/api/v1/orgs/kings/circuits/{circuit_id}/observer-token", headers=bearer(admin))

    identity = tokens.issued[-1]["identity"]
    assert isinstance(identity, str)
    assert not identity.startswith("agent-")
    assert identity.startswith("observer-")


async def test_a_candidate_cannot_take_an_examiners_token(
    client: AsyncClient, make_actor, db_session: AsyncSession, tokens: FakeVoiceTokens
) -> None:
    """Watching an examination is a staff act; sitting one is not.

    The candidate is given a real `trainee` membership of the organisation, so
    this is the access check failing rather than the caller simply not being a
    member: `may_read_org` would have let them through.
    """
    from app.features.tenancy import repository as tenancy_repository

    _, _, circuit_id, trainee_id = await a_live_circuit(client, make_actor, db_session)
    org = await tenancy_repository.organization_by_slug(db_session, "kings")
    assert org is not None
    await tenancy_repository.add_membership(
        db_session, org_id=org.id, user_id=trainee_id, role="trainee", product_surface=None
    )
    await db_session.flush()
    as_trainee = mint_token(
        user_id=trainee_id,
        email="trainee-actor@example.com",
        memberships=(Membership(org_id=org.id, org_slug="kings", role="trainee"),),
        active_org_slug="kings",
    )

    response = await client.post(
        f"/api/v1/orgs/kings/circuits/{circuit_id}/observer-token", headers=bearer(as_trainee)
    )

    assert response.status_code == 403


async def test_a_suspended_organisation_lets_nobody_into_the_room(
    client: AsyncClient, make_actor, db_session: AsyncSession, tokens: FakeVoiceTokens
) -> None:  # type: ignore[no-untyped-def]
    """S-1: a candidate still joined a live circuit after the platform suspended the org."""
    _, candidate, circuit_id, _ = await a_live_circuit(client, make_actor, db_session)
    root = await make_actor("root2@osceguide.com", platform_admin=True)
    suspended = await client.post("/api/v1/platform/organizations/kings/suspend", headers=bearer(root))
    assert suspended.status_code == 200, suspended.text

    response = await client.post(f"/api/v1/me/circuits/{circuit_id}/join-token", headers=bearer(candidate))

    assert response.status_code == 403, response.text
    assert response.json()["code"] == "organization_suspended"
    assert tokens.issued == []


async def test_a_revoked_trainee_cannot_join_their_circuit(
    client: AsyncClient, make_actor, db_session: AsyncSession, tokens: FakeVoiceTokens
) -> None:  # type: ignore[no-untyped-def]
    """S-1: revoking a trainee's access left their slot's room open to them."""
    from app.features.roster import repository as roster_repo

    admin, candidate, circuit_id, user_id = await a_live_circuit(client, make_actor, db_session)
    trainee_id = (await roster_repo.trainee_ids_for_user(db_session, user_id))[0]
    revoked = await client.post(
        f"/api/v1/orgs/kings/trainees/{trainee_id}/access", json={"revoked": True}, headers=bearer(admin)
    )
    assert revoked.status_code == 200, revoked.text

    response = await client.post(f"/api/v1/me/circuits/{circuit_id}/join-token", headers=bearer(candidate))

    assert response.json()["code"] == "trainee_revoked", response.text
    assert tokens.issued == []
