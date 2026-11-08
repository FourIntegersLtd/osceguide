"""The lead assessor (`gp_lead`): invitable on an employer (hire) organisation only, and the
role that settles a station's two marks. Institutions are unchanged."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.features.voice.service import get_room_agents, get_voice_tokens
from tests.http.test_reviews_routes import a_slot
from tests.http.test_station_assessors import two_station_circuit
from tests.support.catalog import create_exam
from tests.support.fakes import FakeRoomAgents, FakeVoiceTokens
from tests.support.tokens import bearer, mint_token

pytestmark = pytest.mark.db


@pytest.fixture(autouse=True)
def voice(client: AsyncClient) -> FakeVoiceTokens:
    """Starting a circuit dials LiveKit; fake it so the file never depends on a developer's .env."""
    fake = FakeVoiceTokens()
    app = client._transport.app  # type: ignore[attr-defined]
    app.dependency_overrides[get_voice_tokens] = lambda: fake
    app.dependency_overrides[get_room_agents] = lambda: FakeRoomAgents()
    return fake


async def _org(client: AsyncClient, make_actor, *, slug: str, org_type: str):  # type: ignore[no-untyped-def]
    root = await make_actor(f"root-{slug}@osceguide.com", platform_admin=True)
    created = await client.post(
        "/api/v1/platform/organizations",
        json={"slug": slug, "name": slug.title(), "org_type": org_type},
        headers=bearer(root),
    )
    assert created.status_code == 201, created.text
    org_id = uuid.UUID(created.json()["id"])
    owner = await make_actor(
        f"owner-{slug}@example.com",
        memberships=(Membership(org_id=org_id, org_slug=slug, role="owner"),),
        active_org_slug=slug,
    )
    await create_exam(client, root, code="sca")
    return org_id, owner, root


async def _invite(client: AsyncClient, owner: str, slug: str, email: str, role: str):  # type: ignore[no-untyped-def]
    return await client.post(
        f"/api/v1/orgs/{slug}/memberships", json={"email": email, "role": role}, headers=bearer(owner)
    )


async def test_an_employer_admin_invites_a_lead_assessor(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, owner, _ = await _org(client, make_actor, slug="acme", org_type="employer")
    added = await _invite(client, owner, "acme", "sara.khan@acme.nhs.uk", "gp_lead")
    assert added.status_code == 201, added.text
    assert added.json()["role"] == "gp_lead"


async def test_an_institution_refuses_a_lead_assessor_by_invite_and_by_role_change(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor
) -> None:
    _, owner, _ = await _org(client, make_actor, slug="kings", org_type="institution")
    refused = await _invite(client, owner, "kings", "lead@kings.ac.uk", "gp_lead")
    assert (refused.status_code, refused.json()["code"]) == (422, "invalid_input"), refused.text
    seated = await _invite(client, owner, "kings", "tutor@kings.ac.uk", "supervisor")
    changed = await client.patch(
        f"/api/v1/orgs/kings/memberships/{seated.json()['id']}",
        json={"role": "gp_lead"},
        headers=bearer(owner),
    )
    assert (changed.status_code, changed.json()["code"]) == (422, "invalid_input"), changed.text


async def test_a_lead_assessor_sees_the_lead_review_permission_and_not_sign_off(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor
) -> None:
    org_id, _, _ = await _org(client, make_actor, slug="acme", org_type="employer")
    lead = await make_actor(
        "lead@acme.nhs.uk",
        memberships=(Membership(org_id=org_id, org_slug="acme", role="gp_lead"),),
        active_org_slug="acme",
    )
    caps = await client.get("/api/v1/me/capabilities", headers=bearer(lead))
    assert caps.status_code == 200, caps.text
    can = caps.json()["can"]
    assert (can["lead_review"], can["run_circuits"], can["read_org"]) == (True, True, True)
    assert (can["sign_off_results"], can["manage_team"], can["schedule_sittings"]) == (False, False, False)


async def test_a_lead_assessor_writes_the_lead_review_and_an_assessor_may_not(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    org_id, _, _ = await _org(client, make_actor, slug="acme", org_type="employer")

    async def member(role: str) -> str:
        return await make_actor(
            f"{role}@acme.nhs.uk",
            memberships=(Membership(org_id=org_id, org_slug="acme", role=role),),
            active_org_slug="acme",
        )

    lead, assessor = await member("gp_lead"), await member("supervisor")
    slot_id = await a_slot(db_session, org_id)
    url = f"/api/v1/orgs/acme/slots/{slot_id}/gp-lead-review"
    for method, body in (("GET", None), ("PUT", {"revision": 0, "notes": "x"}), ("DELETE", None)):
        refused = await client.request(method, url, json=body, headers=bearer(assessor))
        assert (refused.status_code, refused.json()["code"]) == (403, "forbidden"), (method, refused.text)
    saved = await client.put(url, json={"revision": 0, "notes": "Settled"}, headers=bearer(lead))
    assert saved.status_code == 200, saved.text
    assert (await client.get(url, headers=bearer(lead))).json()["notes"] == "Settled"
    assert (await client.delete(url, headers=bearer(lead))).status_code == 204


async def test_an_employer_with_a_lead_assessor_cannot_become_an_institution(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor
) -> None:
    _, owner, root = await _org(client, make_actor, slug="hirecorp", org_type="employer")
    assert (await _invite(client, owner, "hirecorp", "lead@example.com", "gp_lead")).status_code == 201
    refused = await client.patch(
        "/api/v1/platform/organizations/hirecorp", json={"org_type": "institution"}, headers=bearer(root)
    )
    assert (refused.status_code, refused.json()["code"]) == (422, "invalid_input"), refused.text


async def test_a_lead_assessor_not_named_on_a_station_observes_it_and_a_plain_assessor_does_not(  # type: ignore[no-untyped-def]
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:
    s = await two_station_circuit(client, db_session, make_actor)
    from app.features.tenancy import repository as tenancy_repository

    org = await tenancy_repository.organization_by_slug(db_session, "kings")
    assert org is not None
    started = await client.post(
        f"/api/v1/orgs/kings/circuits/{s.circuit['id']}/start", headers=bearer(s.admin)
    )
    assert started.status_code == 200, started.text
    observe = f"/api/v1/orgs/kings/circuits/{s.circuit['id']}/observer-token"
    gp_lead = mint_token(
        user_id=uuid.uuid4(),
        email="gplead@example.com",
        memberships=(Membership(org_id=org.id, org_slug="kings", role="gp_lead"),),
        active_org_slug="kings",
    )

    refused = await client.post(observe, headers=bearer(s.other[1]))
    assert (refused.status_code, refused.json()["code"]) == (403, "not_your_station")
    allowed = await client.post(observe, headers=bearer(gp_lead))
    assert allowed.status_code == 200, allowed.text
