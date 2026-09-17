"""Rostering, and the group membership b2b does not store."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.core.auth import Membership
from tests.support.catalog import create_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def org_with_admin(client: AsyncClient, make_actor, slug: str = "kings"):  # type: ignore[no-untyped-def]
    root = await make_actor(f"root-{slug}@osceguide.com", platform_admin=True)
    created = await client.post(
        "/api/v1/platform/organizations",
        json={"slug": slug, "name": slug.title(), "org_type": "institution"},
        headers=bearer(root),
    )
    org_id = uuid.UUID(created.json()["id"])
    admin = await make_actor(
        f"admin-{slug}@example.com",
        memberships=(Membership(org_id=org_id, org_slug=slug, role="owner"),),
        active_org_slug=slug,
    )
    # Nothing is seeded, so the exam an org's stations name has to be written
    # first — by a platform admin, which is exactly who is holding this token.
    await create_exam(client, root, code="sca")
    return org_id, admin


async def add_trainee(client: AsyncClient, admin: str, email: str, slug: str = "kings") -> str:
    response = await client.post(
        f"/api/v1/orgs/{slug}/trainees", json={"email": email}, headers=bearer(admin)
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def test_a_trainee_is_added_and_listed(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    await add_trainee(client, admin, "alice@example.com")
    response = await client.get("/api/v1/orgs/kings/trainees", headers=bearer(admin))
    assert [t["email"] for t in response.json()["items"]] == ["alice@example.com"]


async def test_the_same_email_twice_conflicts(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    await add_trainee(client, admin, "dupe@example.com")
    response = await client.post(
        "/api/v1/orgs/kings/trainees", json={"email": "DUPE@example.com"}, headers=bearer(admin)
    )
    assert response.status_code == 409
    assert response.json()["code"] == "trainee_exists"


async def test_access_can_be_revoked_and_restored(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    trainee_id = await add_trainee(client, admin, "revoke@example.com")

    revoked = await client.post(
        f"/api/v1/orgs/kings/trainees/{trainee_id}/access",
        json={"revoked": True},
        headers=bearer(admin),
    )
    assert revoked.json()["access_revoked"] is True

    restored = await client.post(
        f"/api/v1/orgs/kings/trainees/{trainee_id}/access",
        json={"revoked": False},
        headers=bearer(admin),
    )
    assert restored.json()["access_revoked"] is False


async def test_group_membership_is_stored_not_matched(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """b2b matches a trainee's cohort string against a group's label. Here the
    membership is a row, so renaming the group changes nothing about who is in it."""
    _, admin = await org_with_admin(client, make_actor)
    group = (
        await client.post(
            "/api/v1/orgs/kings/trainee-groups",
            json={"label": "Cohort A"},
            headers=bearer(admin),
        )
    ).json()
    first = await add_trainee(client, admin, "g1@example.com")
    second = await add_trainee(client, admin, "g2@example.com")

    response = await client.put(
        f"/api/v1/orgs/kings/trainee-groups/{group['id']}/members",
        json={"trainee_ids": [first, second]},
        headers=bearer(admin),
    )
    assert response.status_code == 200
    assert response.json()["member_count"] == 2


async def test_two_spellings_of_a_label_are_one_group(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    await client.post("/api/v1/orgs/kings/trainee-groups", json={"label": "Cohort A"}, headers=bearer(admin))
    response = await client.post(
        "/api/v1/orgs/kings/trainee-groups", json={"label": "  cohort   a "}, headers=bearer(admin)
    )
    assert response.status_code == 409
    assert response.json()["code"] == "group_exists"


async def test_setting_members_replaces_them(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    group = (
        await client.post("/api/v1/orgs/kings/trainee-groups", json={"label": "G"}, headers=bearer(admin))
    ).json()
    first = await add_trainee(client, admin, "r1@example.com")
    second = await add_trainee(client, admin, "r2@example.com")
    url = f"/api/v1/orgs/kings/trainee-groups/{group['id']}/members"

    await client.put(url, json={"trainee_ids": [first, second]}, headers=bearer(admin))
    replaced = await client.put(url, json={"trainee_ids": [first]}, headers=bearer(admin))
    assert replaced.json()["member_count"] == 1


async def test_a_trainee_from_another_org_cannot_be_added(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, kings_admin = await org_with_admin(client, make_actor, "kings")
    _, guys_admin = await org_with_admin(client, make_actor, "guys")
    outsider = await add_trainee(client, guys_admin, "outsider@example.com", slug="guys")
    group = (
        await client.post(
            "/api/v1/orgs/kings/trainee-groups", json={"label": "G"}, headers=bearer(kings_admin)
        )
    ).json()

    response = await client.put(
        f"/api/v1/orgs/kings/trainee-groups/{group['id']}/members",
        json={"trainee_ids": [outsider]},
        headers=bearer(kings_admin),
    )
    assert response.status_code == 404
    assert response.json()["code"] == "trainee_not_found"


async def test_resolving_a_roster_merges_explicit_and_group_members(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    group = (
        await client.post("/api/v1/orgs/kings/trainee-groups", json={"label": "G"}, headers=bearer(admin))
    ).json()
    named = await add_trainee(client, admin, "named@example.com")
    member = await add_trainee(client, admin, "member@example.com")
    await client.put(
        f"/api/v1/orgs/kings/trainee-groups/{group['id']}/members",
        json={"trainee_ids": [member]},
        headers=bearer(admin),
    )

    response = await client.post(
        "/api/v1/orgs/kings/roster/resolve",
        json={"trainee_ids": [named], "group_ids": [group["id"]]},
        headers=bearer(admin),
    )
    assert response.json()["trainee_ids"] == [named, member]
    assert response.json()["warnings"] == []


async def test_an_empty_linked_group_is_reported(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The warning is what stops an examination starting without half its
    candidates."""
    _, admin = await org_with_admin(client, make_actor)
    group = (
        await client.post("/api/v1/orgs/kings/trainee-groups", json={"label": "Empty"}, headers=bearer(admin))
    ).json()
    response = await client.post(
        "/api/v1/orgs/kings/roster/resolve",
        json={"trainee_ids": [], "group_ids": [group["id"]]},
        headers=bearer(admin),
    )
    assert response.json()["trainee_ids"] == []
    assert response.json()["warnings"] == [{"code": "empty_group", "group_id": group["id"]}]


async def test_another_orgs_roster_is_invisible(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, kings_admin = await org_with_admin(client, make_actor, "kings")
    _, guys_admin = await org_with_admin(client, make_actor, "guys")
    await add_trainee(client, kings_admin, "private@example.com")
    response = await client.get("/api/v1/orgs/guys/trainees", headers=bearer(guys_admin))
    assert response.json()["items"] == []


async def test_rostering_somebody_who_already_has_an_account_links_them(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """`trainees.user_id` was modelled and never written by anything.

    A slot names a `users.id`; a released result is keyed on `trainees.id`.
    Without the link they are two unconnected records for one person.
    """
    org_id, admin = await org_with_admin(client, make_actor)
    await make_actor("already@example.com")

    created = await client.post(
        "/api/v1/orgs/kings/trainees", json={"email": "already@example.com"}, headers=bearer(admin)
    )
    assert created.status_code == 201, created.text
    assert created.json()["user_id"] is not None


async def test_registering_claims_the_roster_entry_that_was_waiting(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The usual order: an institution invites by email, the person signs up later."""
    org_id, admin = await org_with_admin(client, make_actor)
    trainee_id = await add_trainee(client, admin, "invited@example.com")

    registered = await client.post(
        "/api/v1/auth/register",
        json={"email": "invited@example.com", "name": "Invited", "password": "Str0ng-Passw0rd!"},
    )
    assert registered.status_code in (200, 201), registered.text
    user_id = registered.json()["user"]["id"]

    listed = (await client.get("/api/v1/orgs/kings/trainees", headers=bearer(admin))).json()
    entry = next(row for row in listed["items"] if row["id"] == trainee_id)
    assert entry["user_id"] == user_id
