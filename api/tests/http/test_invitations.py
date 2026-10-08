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
from tests.support.people import mark_signed_in
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


async def test_the_console_seats_the_first_owner(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    """The organisation has no admin yet, so the platform admin does it."""
    root, org_id = await provisioned(client, make_actor)
    # `invited` means "still waiting on their invitation": the dean has an account and has signed in.
    await make_actor("dean@ashford.ac.uk")
    await mark_signed_in(db_session, email="dean@ashford.ac.uk")

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
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json() == {"status": "accepted", "email": "new.dean@ashford.ac.uk"}
    login = await client.post(
        "/api/v1/auth/login", json={"email": "new.dean@ashford.ac.uk", "password": "Str0ng-Passw0rd!"}
    )
    assert login.status_code == 200, login.text
    assert login.json()["user"]["active_org_slug"] == "ashford"
    assert [m["role"] for m in login.json()["user"]["memberships"]] == ["owner"]


async def test_the_console_may_hand_a_new_account_a_temporary_password(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """When the invitation email cannot be delivered, the console relays a password by
    hand: no email is queued, the person can sign in at once, and that first sign-in
    may only change the password."""
    root, _ = await provisioned(client, make_actor)
    seated = await client.post(
        "/api/v1/platform/organizations/ashford/memberships",
        json={"email": "hand.dean@ashford.ac.uk", "role": "owner", "temporary_password": "Temp-Passw0rd!"},
        headers=bearer(root),
    )
    assert seated.status_code == 201, seated.text
    assert seated.json()["invited"] is False
    assert await queued_invitations(db_session) == []

    login = await client.post(
        "/api/v1/auth/login", json={"email": "hand.dean@ashford.ac.uk", "password": "Temp-Passw0rd!"}
    )
    assert login.status_code == 200, login.text
    assert login.json()["user"]["must_change_password"] is True
    assert [m["role"] for m in login.json()["user"]["memberships"]] == ["owner"]

    audit = await client.get("/api/v1/platform/organizations/ashford/audit", headers=bearer(root))
    assert audit.status_code == 200, audit.text
    assert "Granted owner to hand.dean@ashford.ac.uk (temporary password)" in {
        row["summary"] for row in audit.json()["items"]
    }


async def test_a_weak_temporary_password_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root, _ = await provisioned(client, make_actor)
    seated = await client.post(
        "/api/v1/platform/organizations/ashford/memberships",
        json={"email": "weak.dean@ashford.ac.uk", "role": "owner", "temporary_password": "short"},
        headers=bearer(root),
    )
    assert seated.status_code == 422, seated.text
    assert seated.json()["code"] == "weak_password"


async def test_a_temporary_password_never_touches_an_existing_account(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root, _ = await provisioned(client, make_actor)
    registered = await client.post(
        "/api/v1/auth/register",
        json={"email": "already@ashford.ac.uk", "name": "Already Here", "password": "Their-0wn-Passw0rd"},
    )
    assert registered.status_code == 201, registered.text
    seated = await client.post(
        "/api/v1/platform/organizations/ashford/memberships",
        json={"email": "already@ashford.ac.uk", "role": "owner", "temporary_password": "Temp-Passw0rd!"},
        headers=bearer(root),
    )
    assert seated.status_code == 201, seated.text
    assert seated.json()["invited"] is False
    login = await client.post(
        "/api/v1/auth/login", json={"email": "already@ashford.ac.uk", "password": "Temp-Passw0rd!"}
    )
    assert login.status_code == 401, login.text
    login = await client.post(
        "/api/v1/auth/login", json={"email": "already@ashford.ac.uk", "password": "Their-0wn-Passw0rd"}
    )
    assert login.status_code == 200, login.text


async def test_a_team_invite_may_hand_a_new_account_a_temporary_password(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """B-1: an org admin can add staff while invitation email is undeliverable."""
    _, org_id = await provisioned(client, make_actor)
    owner = await make_actor(
        "owner@ashford.ac.uk",
        memberships=(Membership(org_id=org_id, org_slug="ashford", role="owner"),),
        active_org_slug="ashford",
    )
    added = await client.post(
        "/api/v1/orgs/ashford/memberships",
        json={"email": "sup@ashford.ac.uk", "role": "supervisor", "temporary_password": "Temp-Passw0rd!"},
        headers=bearer(owner),
    )
    assert added.status_code == 201, added.text
    assert added.json()["invited"] is False
    assert added.json()["temporary_password_applied"] is True
    assert await queued_invitations(db_session) == []
    login = await client.post(
        "/api/v1/auth/login", json={"email": "sup@ashford.ac.uk", "password": "Temp-Passw0rd!"}
    )
    assert login.status_code == 200, login.text
    assert login.json()["user"]["must_change_password"] is True
    audit = await client.get("/api/v1/orgs/ashford/audit", headers=bearer(owner))
    assert "Granted supervisor to sup@ashford.ac.uk (temporary password)" in {
        row["summary"] for row in audit.json()["items"]
    }


async def test_a_team_temporary_password_never_touches_an_existing_account(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    _, org_id = await provisioned(client, make_actor)
    owner = await make_actor(
        "owner@ashford.ac.uk",
        memberships=(Membership(org_id=org_id, org_slug="ashford", role="owner"),),
        active_org_slug="ashford",
    )
    registered = await client.post(
        "/api/v1/auth/register",
        json={"email": "here@ashford.ac.uk", "name": "Here", "password": "Their-0wn-Passw0rd"},
    )
    assert registered.status_code == 201, registered.text
    added = await client.post(
        "/api/v1/orgs/ashford/memberships",
        json={"email": "here@ashford.ac.uk", "role": "supervisor", "temporary_password": "Temp-Passw0rd!"},
        headers=bearer(owner),
    )
    assert added.status_code == 201, added.text
    assert added.json()["temporary_password_applied"] is False
    login = await client.post(
        "/api/v1/auth/login", json={"email": "here@ashford.ac.uk", "password": "Temp-Passw0rd!"}
    )
    assert login.status_code == 401, login.text


async def test_a_roster_add_may_hand_a_new_account_a_temporary_password(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _, org_id = await provisioned(client, make_actor)
    owner = await make_actor(
        "owner@ashford.ac.uk",
        memberships=(Membership(org_id=org_id, org_slug="ashford", role="owner"),),
        active_org_slug="ashford",
    )
    added = await client.post(
        "/api/v1/orgs/ashford/trainees",
        json={"email": "stu@ashford.ac.uk", "temporary_password": "Temp-Passw0rd!"},
        headers=bearer(owner),
    )
    assert added.status_code == 201, added.text
    assert added.json()["temporary_password_applied"] is True
    assert await queued_invitations(db_session) == []
    login = await client.post(
        "/api/v1/auth/login", json={"email": "stu@ashford.ac.uk", "password": "Temp-Passw0rd!"}
    )
    assert login.status_code == 200, login.text
    assert login.json()["user"]["must_change_password"] is True
    audit = await client.get("/api/v1/orgs/ashford/audit", headers=bearer(owner))
    assert "Added stu@ashford.ac.uk to the roster (temporary password)" in {
        row["summary"] for row in audit.json()["items"]
    }


async def test_a_weak_roster_temporary_password_is_refused_and_adds_nobody(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    _, org_id = await provisioned(client, make_actor)
    owner = await make_actor(
        "owner@ashford.ac.uk",
        memberships=(Membership(org_id=org_id, org_slug="ashford", role="owner"),),
        active_org_slug="ashford",
    )
    added = await client.post(
        "/api/v1/orgs/ashford/trainees",
        json={"email": "stu@ashford.ac.uk", "temporary_password": "short"},
        headers=bearer(owner),
    )
    assert added.status_code == 422, added.text
    assert added.json()["code"] == "weak_password"
    listed = await client.get("/api/v1/orgs/ashford/trainees", headers=bearer(owner))
    assert listed.json()["items"] == []


async def test_the_console_reissues_a_password_only_until_it_is_changed(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """P-8: the relayed password is lost -> a new one, until the person chose their own."""
    root, _ = await provisioned(client, make_actor)
    seated = await client.post(
        "/api/v1/platform/organizations/ashford/memberships",
        json={"email": "lost.dean@ashford.ac.uk", "role": "owner", "temporary_password": "Temp-Passw0rd!"},
        headers=bearer(root),
    )
    assert seated.json()["temporary_password_applied"] is True
    user_id = seated.json()["user_id"]
    url = f"/api/v1/platform/users/{user_id}/temporary-password"

    weak = await client.post(url, json={"temporary_password": "short"}, headers=bearer(root))
    assert (weak.status_code, weak.json()["code"]) == (422, "weak_password")

    reissued = await client.post(url, json={"temporary_password": "Second-Passw0rd!"}, headers=bearer(root))
    assert reissued.status_code == 204, reissued.text
    old = await client.post(
        "/api/v1/auth/login", json={"email": "lost.dean@ashford.ac.uk", "password": "Temp-Passw0rd!"}
    )
    assert old.status_code == 401
    login = await client.post(
        "/api/v1/auth/login", json={"email": "lost.dean@ashford.ac.uk", "password": "Second-Passw0rd!"}
    )
    assert login.status_code == 200, login.text
    assert login.json()["user"]["must_change_password"] is True

    # An account that chose its own password is never reset from here.
    chosen = await client.post(
        "/api/v1/auth/register",
        json={"email": "chosen@ashford.ac.uk", "name": "Chosen", "password": "Their-0wn-Passw0rd"},
    )
    chosen_id = chosen.json()["user"]["id"]
    refused = await client.post(
        f"/api/v1/platform/users/{chosen_id}/temporary-password",
        json={"temporary_password": "Second-Passw0rd!"},
        headers=bearer(root),
    )
    assert (refused.status_code, refused.json()["code"]) == (409, "password_already_chosen")


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


async def test_an_invited_person_has_no_display_name_until_they_set_one(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    """The address is not a name: storing it made the dashboard greet "Good morning, tutor@ashford.ac.uk."."""
    from app.features.identity.models import User

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
    name = (
        await db_session.execute(select(User.name).where(User.email == "tutor@ashford.ac.uk"))
    ).scalar_one()
    assert name == ""


async def test_only_an_org_admin_may_schedule_a_sitting(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """`schedule_sittings` is what the dashboard's "Schedule a sitting" reads.

    It matches the create route's own guard.
    """
    _, org_id = await provisioned(client, make_actor)
    supervisor = await make_actor(
        "sup@ashford.ac.uk",
        memberships=(Membership(org_id=org_id, org_slug="ashford", role="supervisor"),),
        active_org_slug="ashford",
    )
    admin = await make_actor(
        "admin@ashford.ac.uk",
        memberships=(Membership(org_id=org_id, org_slug="ashford", role="institution_admin"),),
        active_org_slug="ashford",
    )
    assert (await client.get("/api/v1/me/capabilities", headers=bearer(supervisor))).json()["can"][
        "schedule_sittings"
    ] is False
    assert (await client.get("/api/v1/me/capabilities", headers=bearer(admin))).json()["can"][
        "schedule_sittings"
    ] is True


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
