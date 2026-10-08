"""What may be scheduled and started (S-24, R-41), and whose sittings a workspace shows (T-11)."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.features.tenancy import repository as tenancy_repo
from tests.http.test_examiner_transcript_routes import an_examiner
from tests.http.test_org_read_models import a_circuit, a_sitting, a_user
from tests.http.test_sittings_routes import org_with_admin, published_station
from tests.support.sittings import add_programme, create_sitting_body
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def test_a_retired_or_unactivated_programme_cannot_be_scheduled(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    url = "/api/v1/orgs/kings/sittings"

    programme_id = await add_programme(client, admin, org_slug="kings")
    ok = await client.post(
        url, json=create_sitting_body(name="A", programme_id=programme_id, mode="exam"), headers=bearer(admin)
    )
    assert ok.status_code == 201, ok.text

    await client.patch(
        f"/api/v1/orgs/kings/programmes/{programme_id}", json={"status": "retired"}, headers=bearer(admin)
    )
    refused = await client.post(
        url, json=create_sitting_body(name="B", programme_id=programme_id, mode="exam"), headers=bearer(admin)
    )
    assert (refused.status_code, refused.json()["code"]) == (409, "programme_not_active")


async def test_a_circuit_whose_lead_lost_the_role_cannot_start(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    station = await published_station(client, admin, "kings", "Chest pain")
    candidate = await a_user(db_session, "cand@example.com")
    lead, _ = await an_examiner(db_session, org_id, "lead@example.com")
    circuit = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(candidate)],
        station_version_ids=[station],
        supervisor_user_id=str(lead),
    )
    for membership in await tenancy_repo.memberships_for_user_in_org(db_session, org_id, lead):
        await tenancy_repo.set_membership_role(db_session, org_id, membership.id, role="trainee")
    await db_session.flush()

    refused = await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))
    assert (refused.status_code, refused.json()["code"]) == (409, "lead_cannot_run")


async def test_my_sittings_can_be_scoped_to_one_workspace(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    station = await published_station(client, admin, "kings", "Chest pain")
    root = await make_actor("root-elsewhere@osceguide.com", platform_admin=True)
    other = await client.post(
        "/api/v1/platform/organizations",
        json={"slug": "elsewhere", "name": "Elsewhere", "org_type": "institution"},
        headers=bearer(root),
    )
    token = await make_actor(
        "me@example.com",
        memberships=(
            Membership(org_id=org_id, org_slug="kings", role="trainee"),
            Membership(org_id=uuid.UUID(other.json()["id"]), org_slug="elsewhere", role="trainee"),
        ),
        active_org_slug="kings",
    )
    candidate_id = await a_user(db_session, "me@example.com")
    await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(candidate_id)],
        station_version_ids=[station],
    )

    everywhere = (await client.get("/api/v1/me/sittings", headers=bearer(token))).json()
    here = (await client.get("/api/v1/me/sittings?org_slug=kings", headers=bearer(token))).json()
    there = (await client.get("/api/v1/me/sittings?org_slug=elsewhere", headers=bearer(token))).json()
    assert (len(everywhere["items"]), len(here["items"]), there["items"]) == (1, 1, [])
