"""Bulk team actions the retiring b2b client offered and the platform did
not: revoking a selection of memberships, and resending a selection's
invitations, both in one request.

Each route is a thin wrapper around the single-row route it matches
(`POST /memberships/{id}/revoke`, `POST /memberships/{id}/resend-invitation`);
these tests prove the batch reports the right outcome per row rather than
re-testing those routes' own business rules again.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.notifications.models import OutboundMessage
from tests.http.test_tenancy_routes import member_token, seed_org
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

KINGS = "/api/v1/orgs/kings"


async def a_membership(
    client: AsyncClient, admin: str, email: str, role: str = "supervisor", slug: str = "kings"
) -> str:
    response = await client.post(
        f"/api/v1/orgs/{slug}/memberships", json={"email": email, "role": role}, headers=bearer(admin)
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


async def invitations_to(db_session: AsyncSession, recipient: str) -> list[OutboundMessage]:
    stmt = (
        select(OutboundMessage)
        .where(OutboundMessage.template_key == "invitation", OutboundMessage.recipient == recipient)
        .order_by(OutboundMessage.available_at)
    )
    return list((await db_session.execute(stmt)).scalars())


# --------------------------------------------------------------------------
# POST /memberships/bulk/revoke
# --------------------------------------------------------------------------


async def test_a_selection_of_memberships_is_revoked_in_one_request(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor, "kings")
    admin = await member_token(make_actor, org_id, "kings", "owner")
    first = await a_membership(client, admin, "first@example.com")
    second = await a_membership(client, admin, "second@example.com")

    response = await client.post(
        f"{KINGS}/memberships/bulk/revoke",
        json={"membership_ids": [first, second]},
        headers=bearer(admin),
    )
    assert response.status_code == 200, response.text
    assert response.json()["results"] == [
        {"membership_id": first, "outcome": "revoked"},
        {"membership_id": second, "outcome": "revoked"},
    ]

    listed = (await client.get(f"{KINGS}/memberships", headers=bearer(admin))).json()
    statuses = {m["id"]: m["status"] for m in listed["items"]}
    assert statuses[first] == "revoked"
    assert statuses[second] == "revoked"


async def test_an_already_revoked_membership_is_reported_not_re_revoked(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor, "kings")
    admin = await member_token(make_actor, org_id, "kings", "owner")
    membership_id = await a_membership(client, admin, "twice@example.com")
    await client.post(f"{KINGS}/memberships/{membership_id}/revoke", headers=bearer(admin))

    response = await client.post(
        f"{KINGS}/memberships/bulk/revoke", json={"membership_ids": [membership_id]}, headers=bearer(admin)
    )
    assert response.status_code == 200, response.text
    assert response.json()["results"] == [{"membership_id": membership_id, "outcome": "already_revoked"}]


async def test_an_unknown_membership_id_is_not_found_not_fatal(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor, "kings")
    admin = await member_token(make_actor, org_id, "kings", "owner")
    real = await a_membership(client, admin, "real@example.com")
    missing = str(uuid.uuid4())

    response = await client.post(
        f"{KINGS}/memberships/bulk/revoke",
        json={"membership_ids": [real, missing]},
        headers=bearer(admin),
    )
    assert response.status_code == 200, response.text
    assert response.json()["results"] == [
        {"membership_id": real, "outcome": "revoked"},
        {"membership_id": missing, "outcome": "not_found"},
    ]


async def test_a_repeated_membership_id_is_processed_once(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor, "kings")
    admin = await member_token(make_actor, org_id, "kings", "owner")
    membership_id = await a_membership(client, admin, "repeated@example.com")

    response = await client.post(
        f"{KINGS}/memberships/bulk/revoke",
        json={"membership_ids": [membership_id, membership_id]},
        headers=bearer(admin),
    )
    assert response.status_code == 200, response.text
    assert response.json()["results"] == [{"membership_id": membership_id, "outcome": "revoked"}]


async def test_an_admin_of_one_org_cannot_bulk_revoke_anothers_membership(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """Tenant isolation: an id from another organisation is `not_found`, never touched."""
    kings_id = await seed_org(client, make_actor, "kings")
    guys_id = await seed_org(client, make_actor, "guys")
    kings_admin = await member_token(make_actor, kings_id, "kings", "owner")
    guys_admin = await member_token(make_actor, guys_id, "guys", "owner")
    theirs = await a_membership(client, guys_admin, "theirs@example.com", slug="guys")

    response = await client.post(
        f"{KINGS}/memberships/bulk/revoke", json={"membership_ids": [theirs]}, headers=bearer(kings_admin)
    )
    assert response.status_code == 200, response.text
    assert response.json()["results"] == [{"membership_id": theirs, "outcome": "not_found"}]

    still_theirs = (await client.get("/api/v1/orgs/guys/memberships", headers=bearer(guys_admin))).json()
    assert next(m for m in still_theirs["items"] if m["id"] == theirs)["status"] == "active"


async def test_a_supervisor_cannot_bulk_revoke_memberships(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor, "kings")
    admin = await member_token(make_actor, org_id, "kings", "owner")
    membership_id = await a_membership(client, admin, "supervised@example.com")
    supervisor = await member_token(make_actor, org_id, "kings", "supervisor")

    refused = await client.post(
        f"{KINGS}/memberships/bulk/revoke",
        json={"membership_ids": [membership_id]},
        headers=bearer(supervisor),
    )
    assert refused.status_code == 403, refused.text


# --------------------------------------------------------------------------
# POST /memberships/bulk/resend-invitation
# --------------------------------------------------------------------------


async def test_a_selection_of_memberships_is_reinvited_in_one_request(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor, "kings")
    admin = await member_token(make_actor, org_id, "kings", "owner")
    membership_id = await a_membership(client, admin, "lost@example.com")

    response = await client.post(
        f"{KINGS}/memberships/bulk/resend-invitation",
        json={"membership_ids": [membership_id]},
        headers=bearer(admin),
    )
    assert response.status_code == 200, response.text
    assert response.json()["results"] == [{"membership_id": membership_id, "outcome": "sent"}]
    assert len(await invitations_to(db_session, "lost@example.com")) == 2


async def test_someone_who_already_accepted_is_reported_not_resent(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor, "kings")
    admin = await member_token(make_actor, org_id, "kings", "owner")
    membership_id = await a_membership(client, admin, "joined@example.com")
    queued = await invitations_to(db_session, "joined@example.com")
    await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": queued[0].payload["token"], "password": "Str0ng-Passw0rd!"},  # type: ignore[attr-defined]
    )

    response = await client.post(
        f"{KINGS}/memberships/bulk/resend-invitation",
        json={"membership_ids": [membership_id]},
        headers=bearer(admin),
    )
    assert response.status_code == 200, response.text
    assert response.json()["results"] == [{"membership_id": membership_id, "outcome": "already_accepted"}]
    assert len(await invitations_to(db_session, "joined@example.com")) == 1


async def test_an_unknown_membership_id_in_a_resend_batch_is_not_found(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor, "kings")
    admin = await member_token(make_actor, org_id, "kings", "owner")
    missing = str(uuid.uuid4())

    response = await client.post(
        f"{KINGS}/memberships/bulk/resend-invitation",
        json={"membership_ids": [missing]},
        headers=bearer(admin),
    )
    assert response.status_code == 200, response.text
    assert response.json()["results"] == [{"membership_id": missing, "outcome": "not_found"}]
