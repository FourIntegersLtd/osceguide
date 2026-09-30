"""The tenancy contract, including the access matrix.

Every org-scoped route is exercised by each role, because "who may call this"
is the part most likely to rot silently.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def seed_org(client: AsyncClient, make_actor, slug: str = "kings") -> uuid.UUID:  # type: ignore[no-untyped-def]
    """Create an org through the platform-admin route, as an admin who exists."""
    token = await make_actor(f"root-{slug}@osceguide.com", platform_admin=True)
    response = await client.post(
        "/api/v1/platform/organizations",
        json={"slug": slug, "name": slug.title(), "org_type": "institution"},
        headers=bearer(token),
    )
    assert response.status_code == 201, response.text
    return uuid.UUID(response.json()["id"])


async def member_token(make_actor, org_id: uuid.UUID, slug: str, role: str) -> str:  # type: ignore[no-untyped-def]
    return await make_actor(
        f"{role}-{slug}@example.com",
        memberships=(Membership(org_id=org_id, org_slug=slug, role=role),),
        active_org_slug=slug,
    )


# --------------------------------------------------------------------------
# Platform administration
# --------------------------------------------------------------------------


async def test_a_platform_admin_can_provision_an_organisation(client: AsyncClient, make_actor) -> None:
    org_id = await seed_org(client, make_actor)
    assert org_id


async def test_an_ordinary_user_cannot_provision_an_organisation(client: AsyncClient, make_actor) -> None:
    response = await client.post(
        "/api/v1/platform/organizations",
        json={"slug": "sneaky", "name": "Sneaky", "org_type": "institution"},
        headers=bearer(await make_actor()),
    )
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


async def test_an_org_admin_is_not_a_platform_admin(client: AsyncClient, make_actor) -> None:
    """The distinction ported from the legacy policy, asserted over HTTP."""
    org_id = await seed_org(client, make_actor)
    response = await client.post(
        "/api/v1/platform/organizations",
        json={"slug": "other", "name": "Other", "org_type": "institution"},
        headers=bearer(await member_token(make_actor, org_id, "kings", "owner")),
    )
    assert response.status_code == 403


async def test_provisioning_the_same_slug_twice_conflicts(client: AsyncClient, make_actor) -> None:
    await seed_org(client, make_actor)
    token = await make_actor("root2@osceguide.com", platform_admin=True)
    response = await client.post(
        "/api/v1/platform/organizations",
        json={"slug": "KINGS", "name": "Dup", "org_type": "institution"},
        headers=bearer(token),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "org_slug_taken"


# --------------------------------------------------------------------------
# Reading an organisation
# --------------------------------------------------------------------------


@pytest.mark.parametrize("role", ["owner", "admin", "institution_admin", "supervisor", "trainee"])
async def test_any_member_may_read_their_organisation(client: AsyncClient, make_actor, role: str) -> None:
    org_id = await seed_org(client, make_actor)
    response = await client.get(
        "/api/v1/orgs/kings", headers=bearer(await member_token(make_actor, org_id, "kings", role))
    )
    assert response.status_code == 200
    assert response.json()["slug"] == "kings"


async def test_a_stranger_may_not_read_an_organisation(client: AsyncClient, make_actor) -> None:
    await seed_org(client, make_actor)
    response = await client.get("/api/v1/orgs/kings", headers=bearer(await make_actor()))
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


async def test_a_member_of_another_org_may_not_read_this_one(client: AsyncClient, make_actor) -> None:
    await seed_org(client, make_actor, "kings")
    other_id = await seed_org(client, make_actor, "guys")
    response = await client.get(
        "/api/v1/orgs/kings", headers=bearer(await member_token(make_actor, other_id, "guys", "owner"))
    )
    assert response.status_code == 403


async def test_an_unknown_organisation_is_not_found_for_a_platform_admin(
    client: AsyncClient, make_actor
) -> None:
    token = await make_actor("root2@osceguide.com", platform_admin=True)
    response = await client.get("/api/v1/orgs/ghost", headers=bearer(token))
    assert response.status_code == 404
    assert response.json()["code"] == "org_not_found"


# --------------------------------------------------------------------------
# Memberships
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("role", "expected"),
    [("owner", 200), ("admin", 200), ("institution_admin", 200), ("supervisor", 403), ("trainee", 403)],
)
async def test_only_admins_may_list_memberships(
    client: AsyncClient, make_actor, role: str, expected: int
) -> None:
    org_id = await seed_org(client, make_actor)
    response = await client.get(
        "/api/v1/orgs/kings/memberships",
        headers=bearer(await member_token(make_actor, org_id, "kings", role)),
    )
    assert response.status_code == expected


async def test_memberships_are_listed_as_a_page(client: AsyncClient, make_actor) -> None:
    org_id = await seed_org(client, make_actor)
    response = await client.get(
        "/api/v1/orgs/kings/memberships",
        headers=bearer(await member_token(make_actor, org_id, "kings", "owner")),
    )
    body = response.json()
    assert "items" in body and "next_cursor" in body


async def test_memberships_can_be_searched_by_email_role_or_user_id(client: AsyncClient, make_actor) -> None:
    org_id = await seed_org(client, make_actor)
    owner_token = await member_token(make_actor, org_id, "kings", "owner")
    added = await client.post(
        "/api/v1/orgs/kings/memberships",
        json={"email": "tutor@kings.example", "role": "supervisor"},
        headers=bearer(owner_token),
    )
    tutor_membership_id = added.json()["id"]
    tutor_user_id = added.json()["user_id"]

    by_email = await client.get(
        "/api/v1/orgs/kings/memberships", params={"search": "TUTOR@kings"}, headers=bearer(owner_token)
    )
    assert [m["id"] for m in by_email.json()["items"]] == [tutor_membership_id]

    by_role = await client.get(
        "/api/v1/orgs/kings/memberships", params={"search": "supervisor"}, headers=bearer(owner_token)
    )
    assert [m["id"] for m in by_role.json()["items"]] == [tutor_membership_id]

    by_user_id = await client.get(
        "/api/v1/orgs/kings/memberships", params={"search": tutor_user_id}, headers=bearer(owner_token)
    )
    assert [m["id"] for m in by_user_id.json()["items"]] == [tutor_membership_id]

    no_match = await client.get(
        "/api/v1/orgs/kings/memberships", params={"search": "nobody-like-this"}, headers=bearer(owner_token)
    )
    assert no_match.json()["items"] == []


async def test_a_membership_row_carries_the_address_it_belongs_to(client: AsyncClient, make_actor) -> None:
    """The list used to answer `email: null` for every row but the one it had
    just invited, which left a team screen showing the front of a user id where
    a person's name should be."""
    org_id = await seed_org(client, make_actor)
    owner = await member_token(make_actor, org_id, "kings", "owner")
    await client.post(
        "/api/v1/orgs/kings/memberships",
        json={"email": "tutor@kings.example", "role": "supervisor"},
        headers=bearer(owner),
    )

    listed = await client.get("/api/v1/orgs/kings/memberships", headers=bearer(owner))
    addresses = {item["email"] for item in listed.json()["items"]}
    assert "tutor@kings.example" in addresses, listed.json()
    assert None not in addresses, "every row on the list is somebody's address"


# --------------------------------------------------------------------------
# Switching workspace
# --------------------------------------------------------------------------


async def test_switching_to_an_org_you_belong_to_reissues_the_token(client: AsyncClient, make_actor) -> None:
    kings = await seed_org(client, make_actor, "kings")
    guys = await seed_org(client, make_actor, "guys")
    token = await make_actor(
        "switcher@example.com",
        memberships=(
            Membership(org_id=kings, org_slug="kings", role="trainee"),
            Membership(org_id=guys, org_slug="guys", role="owner"),
        ),
        active_org_slug="kings",
    )
    response = await client.post(
        "/api/v1/auth/switch-workspace", json={"org_slug": "guys"}, headers=bearer(token)
    )
    assert response.status_code == 200
    assert response.json()["active_org_slug"] == "guys"
    assert response.json()["access_token"] != token


async def test_switching_to_your_own_practice_clears_the_active_org(client: AsyncClient, make_actor) -> None:
    """Belonging to an institution must not be a one-way door.

    Somebody in a cohort still has their own entitlements and their own
    attempts. Without a null workspace there is no token that addresses them,
    so the frontend could offer no way back from an organisation.
    """
    kings = await seed_org(client, make_actor, "kings")
    token = await make_actor(
        "both@example.com",
        memberships=(Membership(org_id=kings, org_slug="kings", role="trainee"),),
        active_org_slug="kings",
    )
    response = await client.post(
        "/api/v1/auth/switch-workspace", json={"org_slug": None}, headers=bearer(token)
    )
    assert response.status_code == 200
    assert response.json()["active_org_slug"] is None
    assert response.json()["active_role"] is None

    capabilities = await client.get(
        "/api/v1/me/capabilities", headers=bearer(response.json()["access_token"])
    )
    assert capabilities.status_code == 200
    assert capabilities.json()["active_org_slug"] is None
    # The membership is still theirs; only the active workspace changed.
    me = await client.get("/api/v1/me", headers=bearer(response.json()["access_token"]))
    assert [m["org_slug"] for m in me.json()["memberships"]] == ["kings"]


async def test_switching_workspace_with_no_body_is_your_own_practice(client: AsyncClient, make_actor) -> None:
    kings = await seed_org(client, make_actor, "kings")
    token = await make_actor(
        "default@example.com",
        memberships=(Membership(org_id=kings, org_slug="kings", role="trainee"),),
        active_org_slug="kings",
    )
    response = await client.post("/api/v1/auth/switch-workspace", json={}, headers=bearer(token))
    assert response.status_code == 200
    assert response.json()["active_org_slug"] is None


async def test_switching_to_an_org_you_do_not_belong_to_is_refused(client: AsyncClient, make_actor) -> None:
    kings = await seed_org(client, make_actor, "kings")
    await seed_org(client, make_actor, "guys")
    response = await client.post(
        "/api/v1/auth/switch-workspace",
        json={"org_slug": "guys"},
        headers=bearer(await member_token(make_actor, kings, "kings", "trainee")),
    )
    assert response.status_code == 403
    assert response.json()["code"] == "not_a_member"


async def test_me_says_what_each_organisation_is_for(client: AsyncClient, make_actor) -> None:
    """The frontend picks a workspace shell from `org_type`.

    An institution examines a cohort and a partner watches a funnel, so they
    get different screens behind the same URL shape. Without this field the
    client would have to infer the arm from a role name, which is how the
    retiring client ended up with a route prefix per arm.
    """
    org_id = await seed_org(client, make_actor, "kings")
    response = await client.get(
        "/api/v1/me", headers=bearer(await member_token(make_actor, org_id, "kings", "owner"))
    )
    assert response.status_code == 200
    membership = response.json()["memberships"][0]
    assert membership["org_slug"] == "kings"
    assert membership["org_type"] == "institution"


# --------------------------------------------------------------------------
# Capabilities read model
# --------------------------------------------------------------------------


async def test_capabilities_are_served_rather_than_recomputed_in_the_browser(
    client: AsyncClient,
    make_actor,  # type: ignore[no-untyped-def]
) -> None:
    """The frontend keeps its own copy of this policy today and uses it to
    decide whether to even issue a request. This endpoint replaces that."""
    org_id = await seed_org(client, make_actor)
    response = await client.get(
        "/api/v1/me/capabilities",
        headers=bearer(await member_token(make_actor, org_id, "kings", "supervisor")),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["active_org_slug"] == "kings"
    assert body["can"]["read_org"] is True
    assert body["can"]["manage_team"] is False


async def test_an_admin_has_the_team_capability(client: AsyncClient, make_actor) -> None:
    org_id = await seed_org(client, make_actor)
    response = await client.get(
        "/api/v1/me/capabilities", headers=bearer(await member_token(make_actor, org_id, "kings", "owner"))
    )
    assert response.json()["can"]["manage_team"] is True


# --------------------------------------------------------------------------
# Inviting the whole team at once
# --------------------------------------------------------------------------


async def test_a_team_can_be_invited_in_one_request(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The retiring client imported staff from a spreadsheet; one at a time was
    all the platform offered, so the import's "Trainees or Staff?" step had no
    destination. An address with no account is invited exactly as a single add
    invites it, and no password is written anywhere.
    """
    from sqlalchemy import select

    from app.features.notifications.models import OutboundMessage

    org_id = await seed_org(client, make_actor, "kings")
    admin = await member_token(make_actor, org_id, "kings", "owner")
    await make_actor("already-here@example.com")

    response = await client.post(
        "/api/v1/orgs/kings/memberships/bulk",
        json={
            "memberships": [
                {"email": "tutor-one@example.com", "role": "supervisor"},
                {"email": "already-here@example.com", "role": "admin"},
                {"email": "Tutor-One@example.com", "role": "supervisor"},
            ]
        },
        headers=bearer(admin),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert [m["email"] for m in body["created"]] == ["tutor-one@example.com", "already-here@example.com"]
    # The repeat is reported rather than fatal, and it is the upload's own
    # duplicate caught before a second invitation went out for one person.
    assert body["skipped"] == [
        {"email": "Tutor-One@example.com", "role": "supervisor", "code": "membership_exists"}
    ]
    assert [m["invited"] for m in body["created"]] == [True, False]

    listed = await client.get("/api/v1/orgs/kings/memberships", headers=bearer(admin))
    assert len(listed.json()["items"]) == 3  # the owner, plus the two just seated

    queued = list(
        (
            await db_session.execute(
                select(OutboundMessage).where(OutboundMessage.template_key == "invitation")
            )
        ).scalars()
    )
    assert [m.recipient for m in queued] == ["tutor-one@example.com"]


async def test_a_person_named_twice_for_two_roles_is_seated_twice(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """A membership is unique per `(org, user, role)`, so this is not a
    duplicate — it is the tutor who supervises and also administers."""
    org_id = await seed_org(client, make_actor, "bothroles")
    admin = await member_token(make_actor, org_id, "bothroles", "owner")

    response = await client.post(
        "/api/v1/orgs/bothroles/memberships/bulk",
        json={
            "memberships": [
                {"email": "wears-two-hats@example.com", "role": "supervisor"},
                {"email": "wears-two-hats@example.com", "role": "admin"},
            ]
        },
        headers=bearer(admin),
    )
    assert response.status_code == 201, response.text
    assert [m["role"] for m in response.json()["created"]] == ["supervisor", "admin"]
    assert response.json()["skipped"] == []


async def test_a_supervisor_cannot_import_a_team(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor, "kings")
    supervisor = await member_token(make_actor, org_id, "kings", "supervisor")

    refused = await client.post(
        "/api/v1/orgs/kings/memberships/bulk",
        json={"memberships": [{"email": "nobody@example.com", "role": "owner"}]},
        headers=bearer(supervisor),
    )
    assert refused.status_code == 403, refused.text
    assert refused.json()["code"] == "forbidden"


async def test_an_empty_team_upload_is_invalid(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor, "kings")
    admin = await member_token(make_actor, org_id, "kings", "owner")

    response = await client.post(
        "/api/v1/orgs/kings/memberships/bulk", json={"memberships": []}, headers=bearer(admin)
    )
    assert response.status_code == 422


# --------------------------------------------------------------------------
# Suspension
# --------------------------------------------------------------------------


async def test_suspending_an_organisation_stops_its_members_working(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Suspension was write-only: it set a status nothing ever read.

    `org_permits_access` existed, with a unit test, and had no caller — so a
    platform admin could suspend an organisation, see it marked suspended, and
    every one of its members would carry on exactly as before.
    """
    root = await make_actor("root-susp@osceguide.com", platform_admin=True)
    org_id = await seed_org(client, make_actor, "suspendable")
    admin = await member_token(make_actor, org_id, "suspendable", "owner")

    before = await client.get("/api/v1/orgs/suspendable/memberships", headers=bearer(admin))
    assert before.status_code == 200, "the member should be working normally first"

    suspended = await client.post("/api/v1/platform/organizations/suspendable/suspend", headers=bearer(root))
    assert suspended.status_code == 200, suspended.text

    after = await client.get("/api/v1/orgs/suspendable/memberships", headers=bearer(admin))
    assert after.status_code == 403, after.text
    assert after.json()["code"] == "organization_suspended"


async def test_a_platform_admin_can_still_reach_a_suspended_organisation(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """Support has to be able to look at the thing it just suspended."""
    root = await make_actor("root-susp2@osceguide.com", platform_admin=True)
    await seed_org(client, make_actor, "lookable")
    await client.post("/api/v1/platform/organizations/lookable/suspend", headers=bearer(root))

    response = await client.get("/api/v1/orgs/lookable", headers=bearer(root))

    assert response.status_code == 200, response.text


async def test_an_organisation_says_which_one_it_sits_under(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """A trust above its hospitals: the column was stored but never returned."""
    from sqlalchemy import update

    from app.features.tenancy.models import Organization

    trust_id = await seed_org(client, make_actor, "trust")
    hospital_id = await seed_org(client, make_actor, "kings")
    await db_session.execute(
        update(Organization).where(Organization.id == hospital_id).values(parent_org_id=trust_id)
    )
    await db_session.flush()

    hospital = await client.get(
        "/api/v1/orgs/kings", headers=bearer(await member_token(make_actor, hospital_id, "kings", "owner"))
    )
    assert hospital.json()["parent_org_id"] == str(trust_id)
    trust = await client.get(
        "/api/v1/orgs/trust", headers=bearer(await member_token(make_actor, trust_id, "trust", "owner"))
    )
    assert trust.json()["parent_org_id"] is None


async def test_an_organisations_audit_log_can_be_narrowed(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The same two filters the platform console has, on one organisation's log."""
    from app.features.tenancy.models import AuditEntry

    org_id = await seed_org(client, make_actor)
    other_id = await seed_org(client, make_actor, "guys")
    db_session.add_all(
        [
            AuditEntry(org_id=org_id, actor_email="ana@example.com", action="trainee.anonymised"),
            AuditEntry(org_id=org_id, actor_email="ana@example.com", action="membership.revoked"),
            AuditEntry(org_id=org_id, actor_email="ben@example.com", action="trainee.deleted"),
            AuditEntry(org_id=other_id, actor_email="ana@example.com", action="trainee.deleted"),
        ]
    )
    await db_session.flush()
    admin = await member_token(make_actor, org_id, "kings", "owner")

    by_person = await client.get(
        "/api/v1/orgs/kings/audit", params={"actor_email": "ANA@example.com"}, headers=bearer(admin)
    )
    assert by_person.status_code == 200, by_person.text
    assert sorted(entry["action"] for entry in by_person.json()["items"]) == [
        "membership.revoked",
        "trainee.anonymised",
    ]

    by_action = await client.get(
        "/api/v1/orgs/kings/audit", params={"action": "trainee."}, headers=bearer(admin)
    )
    assert sorted(entry["action"] for entry in by_action.json()["items"]) == [
        "trainee.anonymised",
        "trainee.deleted",
    ]

    both = await client.get(
        "/api/v1/orgs/kings/audit",
        params={"actor_email": "ben@example.com", "action": "trainee."},
        headers=bearer(admin),
    )
    assert [entry["action"] for entry in both.json()["items"]] == ["trainee.deleted"]


async def test_memberships_filter_on_status(client: AsyncClient, make_actor) -> None:
    org_id = await seed_org(client, make_actor)
    owner = await member_token(make_actor, org_id, "kings", "owner")
    added = await client.post(
        "/api/v1/orgs/kings/memberships",
        json={"email": "leaver@kings.example", "role": "supervisor"},
        headers=bearer(owner),
    )
    leaver_id = added.json()["id"]
    revoked = await client.post(f"/api/v1/orgs/kings/memberships/{leaver_id}/revoke", headers=bearer(owner))
    assert revoked.status_code == 200, revoked.text

    gone = await client.get(
        "/api/v1/orgs/kings/memberships", params={"status": "revoked"}, headers=bearer(owner)
    )
    active = await client.get(
        "/api/v1/orgs/kings/memberships", params={"status": "active"}, headers=bearer(owner)
    )
    assert [row["id"] for row in gone.json()["items"]] == [leaver_id]
    assert leaver_id not in [row["id"] for row in active.json()["items"]]
    assert all(row["status"] == "active" for row in active.json()["items"])

    nonsense = await client.get(
        "/api/v1/orgs/kings/memberships", params={"status": "maybe"}, headers=bearer(owner)
    )
    assert nonsense.status_code == 422
