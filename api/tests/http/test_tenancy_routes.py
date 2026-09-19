"""The tenancy contract, including the access matrix.

Every org-scoped route is exercised by each role, because "who may call this"
is the part most likely to rot silently.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

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
