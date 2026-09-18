"""Seating the first owner, and inviting people who have no account yet.

A freshly provisioned organisation has no members, and the membership route
is org-admin only with platform admins excluded, so nothing could give an
organisation its first owner. And every membership required the person to
have registered first, unprompted. Both are one mechanism: an invitation.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.features.notifications.models import OutboundMessage
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def provisioned(client: AsyncClient, make_actor, slug: str = "ashford"):  # type: ignore[no-untyped-def]
    root = await make_actor(f"root-{slug}@osceguide.com", platform_admin=True)
    created = await client.post(
        "/api/v1/platform/organizations",
        json={"slug": slug, "name": "Ashford Medical School", "org_type": "institution"},
        headers=bearer(root),
    )
    assert created.status_code == 201, created.text
    return root, uuid.UUID(created.json()["id"])


async def queued_invitations(db_session: AsyncSession) -> list[OutboundMessage]:
    stmt = select(OutboundMessage).where(OutboundMessage.template_key == "invitation")
    return list((await db_session.execute(stmt)).scalars())


async def test_the_console_seats_the_first_owner(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The organisation has no admin yet, so the platform admin does it."""
    root, org_id = await provisioned(client, make_actor)
    await make_actor("dean@ashford.ac.uk")

    seated = await client.post(
        "/api/v1/platform/organizations/ashford/memberships",
        json={"email": "dean@ashford.ac.uk", "role": "owner"},
        headers=bearer(root),
    )
    assert seated.status_code == 201, seated.text
    assert seated.json()["role"] == "owner"
    assert seated.json()["invited"] is False

    # The owner can now do what only an org admin may.
    owner = await make_actor(
        "dean2@ashford.ac.uk",
        memberships=(Membership(org_id=org_id, org_slug="ashford", role="owner"),),
        active_org_slug="ashford",
    )
    listed = await client.get("/api/v1/orgs/ashford/memberships", headers=bearer(owner))
    assert listed.status_code == 200
    assert seated.json()["user_id"] in {m["user_id"] for m in listed.json()["items"]}


async def test_seating_invites_an_address_with_no_account(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root, _ = await provisioned(client, make_actor)
    seated = await client.post(
        "/api/v1/platform/organizations/ashford/memberships",
        json={"email": "new.dean@ashford.ac.uk", "role": "owner"},
        headers=bearer(root),
    )
    assert seated.status_code == 201, seated.text
    assert seated.json()["invited"] is True

    invitations = await queued_invitations(db_session)
    assert [m.recipient for m in invitations] == ["new.dean@ashford.ac.uk"]
    assert invitations[0].payload["invited_to"] == "Ashford Medical School"

    confirmed = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": invitations[0].payload["token"], "password": "Str0ng-Passw0rd!"},
    )
    assert confirmed.status_code in (200, 204), confirmed.text
    login = await client.post(
        "/api/v1/auth/login", json={"email": "new.dean@ashford.ac.uk", "password": "Str0ng-Passw0rd!"}
    )
    assert login.status_code == 200, login.text
    assert login.json()["user"]["active_org_slug"] == "ashford"
    assert [m["role"] for m in login.json()["user"]["memberships"]] == ["owner"]


async def test_only_the_console_may_seat(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root, org_id = await provisioned(client, make_actor)
    owner = await make_actor(
        "owner@ashford.ac.uk",
        memberships=(Membership(org_id=org_id, org_slug="ashford", role="owner"),),
        active_org_slug="ashford",
    )
    refused = await client.post(
        "/api/v1/platform/organizations/ashford/memberships",
        json={"email": "x@ashford.ac.uk", "role": "admin"},
        headers=bearer(owner),
    )
    assert refused.status_code == 403


async def test_an_org_admin_invites_a_tutor_who_has_not_registered(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """`user_not_found` is gone: naming somebody is inviting them."""
    root, org_id = await provisioned(client, make_actor)
    owner = await make_actor(
        "owner@ashford.ac.uk",
        memberships=(Membership(org_id=org_id, org_slug="ashford", role="owner"),),
        active_org_slug="ashford",
    )
    added = await client.post(
        "/api/v1/orgs/ashford/memberships",
        json={"email": "tutor@ashford.ac.uk", "role": "supervisor"},
        headers=bearer(owner),
    )
    assert added.status_code == 201, added.text
    assert added.json()["invited"] is True
    assert [m.recipient for m in await queued_invitations(db_session)] == ["tutor@ashford.ac.uk"]

    # Naming them again for the same role is still a conflict, not a second email.
    again = await client.post(
        "/api/v1/orgs/ashford/memberships",
        json={"email": "tutor@ashford.ac.uk", "role": "supervisor"},
        headers=bearer(owner),
    )
    assert again.status_code == 409
    assert again.json()["code"] == "membership_exists"
    assert len(await queued_invitations(db_session)) == 1


async def test_an_invitation_shows_in_the_audit_log(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root, org_id = await provisioned(client, make_actor)
    await client.post(
        "/api/v1/platform/organizations/ashford/memberships",
        json={"email": "first@ashford.ac.uk", "role": "owner"},
        headers=bearer(root),
    )
    owner = await make_actor(
        "owner@ashford.ac.uk",
        memberships=(Membership(org_id=org_id, org_slug="ashford", role="owner"),),
        active_org_slug="ashford",
    )
    audit = await client.get("/api/v1/orgs/ashford/audit", headers=bearer(owner))
    summaries = [row["summary"] for row in audit.json()["items"]]
    assert "Granted owner to first@ashford.ac.uk (invited)" in summaries


async def test_seating_the_same_person_twice_conflicts(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Two clicks on the console must not mint a second set-password token for
    somebody who already has a live one."""
    root, _ = await provisioned(client, make_actor)
    body = {"email": "twice@ashford.ac.uk", "role": "owner"}

    first = await client.post(
        "/api/v1/platform/organizations/ashford/memberships", json=body, headers=bearer(root)
    )
    second = await client.post(
        "/api/v1/platform/organizations/ashford/memberships", json=body, headers=bearer(root)
    )
    assert first.status_code == 201, first.text
    assert second.status_code == 409
    assert second.json()["code"] == "membership_exists"
    assert len(await queued_invitations(db_session)) == 1


async def test_seating_into_an_organisation_that_does_not_exist(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root-nowhere@osceguide.com", platform_admin=True)
    refused = await client.post(
        "/api/v1/platform/organizations/nowhere/memberships",
        json={"email": "someone@nowhere.ac.uk", "role": "owner"},
        headers=bearer(root),
    )
    assert refused.status_code == 404
    assert refused.json()["code"] == "org_not_found"


async def test_a_second_institution_naming_the_same_person_does_not_reinvite(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """An invitation is keyed on its token, so a second one would be a second
    live password link. The account created by the first invitation is what
    stops it: the second institution finds an existing user and links to it."""
    root, ashford_id = await provisioned(client, make_actor, "ashford")
    await provisioned(client, make_actor, "borough")

    for slug in ("ashford", "borough"):
        seated = await client.post(
            f"/api/v1/platform/organizations/{slug}/memberships",
            json={"email": "shared@nhs.uk", "role": "owner"},
            headers=bearer(root),
        )
        assert seated.status_code == 201, seated.text

    invitations = await queued_invitations(db_session)
    assert [m.recipient for m in invitations] == ["shared@nhs.uk"]
