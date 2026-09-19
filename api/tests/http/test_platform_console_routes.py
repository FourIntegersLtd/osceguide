"""The platform console: the one part of the API that reads across tenants.

Which is exactly why every test here is also a test of who may call it.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def an_org(client: AsyncClient, root: str, slug: str) -> dict:
    created = await client.post(
        "/api/v1/platform/organizations",
        json={"slug": slug, "name": slug.title(), "org_type": "institution"},
        headers=bearer(root),
    )
    assert created.status_code == 201, created.text
    return created.json()


async def test_the_console_lists_every_organisation(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await an_org(client, root, "kings")
    await an_org(client, root, "guys")

    listed = await client.get("/api/v1/platform/organizations", headers=bearer(root))
    assert listed.status_code == 200, listed.text
    assert {o["slug"] for o in listed.json()["items"]} >= {"kings", "guys"}


async def test_an_organisation_can_be_renamed_but_not_re_slugged(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Every foreign key points at `id`; the slug is the URL, not a field."""
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await an_org(client, root, "kings")

    updated = await client.patch(
        "/api/v1/platform/organizations/kings",
        json={"name": "King's College London", "slug": "kcl"},
        headers=bearer(root),
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "King's College London"
    assert updated.json()["slug"] == "kings"


async def test_a_suspension_can_be_lifted(client: AsyncClient, make_actor, db_session: AsyncSession) -> None:  # type: ignore[no-untyped-def]
    """Suspending had no inverse, and an action with none is one nobody dares use."""
    root = await make_actor("root@osceguide.com", platform_admin=True)
    org = await an_org(client, root, "kings")
    member = await make_actor(
        "member@kings.example.com",
        memberships=(Membership(org_id=uuid.UUID(org["id"]), org_slug="kings", role="owner"),),
        active_org_slug="kings",
    )

    await client.post("/api/v1/platform/organizations/kings/suspend", headers=bearer(root))
    blocked = await client.get("/api/v1/orgs/kings/trainees", headers=bearer(member))
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "organization_suspended"

    restored = await client.post("/api/v1/platform/organizations/kings/restore", headers=bearer(root))
    assert restored.status_code == 200, restored.text
    assert restored.json()["status"] == "active"
    assert (await client.get("/api/v1/orgs/kings/trainees", headers=bearer(member))).status_code == 200


async def test_the_console_finds_an_account_by_part_of_its_email(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await make_actor("lost.account@hospital.nhs.uk")

    found = await client.get("/api/v1/platform/users?q=lost.account", headers=bearer(root))
    assert found.status_code == 200, found.text
    assert [u["email"] for u in found.json()["items"]] == ["lost.account@hospital.nhs.uk"]


async def test_the_console_grants_and_revokes_itself(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from app.features.identity import repository as identity_repo

    root = await make_actor("root@osceguide.com", platform_admin=True)
    await make_actor("newadmin@osceguide.com")
    user = await identity_repo.user_by_email(db_session, "newadmin@osceguide.com")
    assert user is not None

    granted = await client.put(
        f"/api/v1/platform/users/{user.id}/platform-admin",
        json={"is_platform_admin": True},
        headers=bearer(root),
    )
    assert granted.status_code == 200, granted.text

    revoked = await client.put(
        f"/api/v1/platform/users/{user.id}/platform-admin",
        json={"is_platform_admin": False},
        headers=bearer(root),
    )
    assert revoked.status_code == 200, revoked.text


async def test_granting_to_nobody_is_a_refusal(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    response = await client.put(
        f"/api/v1/platform/users/{uuid.uuid4()}/platform-admin",
        json={"is_platform_admin": True},
        headers=bearer(root),
    )
    assert response.status_code == 404
    assert response.json()["code"] == "user_not_found"


async def test_the_overview_counts_rather_than_lists(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await an_org(client, root, "kings")

    overview = await client.get("/api/v1/platform/overview", headers=bearer(root))
    assert overview.status_code == 200, overview.text
    assert overview.json()["organizations"] >= 1
    assert overview.json()["users"] >= 1


async def test_every_console_route_is_refused_to_an_org_admin(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """An institution's owner runs their institution, not the platform.

    The legacy policy is emphatic that the two do not inherit each other, and
    this is the half that is easy to forget.
    """
    root = await make_actor("root@osceguide.com", platform_admin=True)
    org = await an_org(client, root, "kings")
    owner = await make_actor(
        "owner@kings.example.com",
        memberships=(Membership(org_id=uuid.UUID(org["id"]), org_slug="kings", role="owner"),),
        active_org_slug="kings",
    )

    for method, path, body in (
        ("get", "/api/v1/platform/organizations", None),
        ("patch", "/api/v1/platform/organizations/kings", {"name": "Mine now"}),
        ("post", "/api/v1/platform/organizations/kings/restore", None),
        ("get", "/api/v1/platform/users", None),
        ("get", "/api/v1/platform/overview", None),
        ("put", f"/api/v1/platform/users/{uuid.uuid4()}/platform-admin", {"is_platform_admin": True}),
    ):
        call = getattr(client, method)
        response = await (
            call(path, json=body, headers=bearer(owner)) if body else call(path, headers=bearer(owner))
        )
        assert response.status_code == 403, f"{method} {path} returned {response.status_code}"


async def test_the_account_search_can_be_narrowed_to_console_users(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The team screen used to guess who was an admin from the whole list."""
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await make_actor("plain@example.com")

    admins = await client.get("/api/v1/platform/users?platform_admin=true", headers=bearer(root))
    assert admins.status_code == 200, admins.text
    emails = {row["email"] for row in admins.json()["items"]}
    assert "root@osceguide.com" in emails
    assert "plain@example.com" not in emails
    assert all(row["is_platform_admin"] for row in admins.json()["items"])

    others = await client.get("/api/v1/platform/users?platform_admin=false", headers=bearer(root))
    assert "plain@example.com" in {row["email"] for row in others.json()["items"]}


async def test_deactivating_an_account_ends_its_sessions_now(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Not at the next refresh: the access token is refused on its next request."""
    from tests.http.test_identity_routes import register

    root = await make_actor("root@osceguide.com", platform_admin=True)
    registered = (await register(client, email="leaver@example.com")).json()
    access, refresh = registered["access_token"], registered["refresh_token"]
    assert (await client.get("/api/v1/me", headers=bearer(access))).status_code == 200
    user_id = registered["user"]["id"]

    gone = await client.patch(
        f"/api/v1/platform/users/{user_id}", json={"status": "deactivated"}, headers=bearer(root)
    )
    assert gone.status_code == 200, gone.text

    refused = await client.get("/api/v1/me", headers=bearer(access))
    assert refused.status_code == 401
    assert refused.json()["code"] == "account_suspended"
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})).status_code == 401

    history = await client.get(f"/api/v1/platform/users/{user_id}/audit", headers=bearer(root))
    assert history.json()["items"][0]["action"] == "user.deactivated"

    back = await client.patch(
        f"/api/v1/platform/users/{user_id}", json={"status": "active"}, headers=bearer(root)
    )
    assert back.status_code == 200
    history = await client.get(f"/api/v1/platform/users/{user_id}/audit", headers=bearer(root))
    assert sorted(row["action"] for row in history.json()["items"]) == [
        "user.deactivated",
        "user.reactivated",
    ]
    # The old sessions stay ended; signing in again is how they come back.
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})).status_code == 401
