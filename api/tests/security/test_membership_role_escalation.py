"""Privilege escalation through the membership `role` field (security regression).

Finding SEC-001 (High). `PATCH /orgs/{slug}/memberships/{id}` and
`POST /orgs/{slug}/memberships` are gated by `OrgAdmin`, which admits
`partner_admin`. The `role` on the body is a free string (`min_length=1,
max_length=32`, no allow-list), written verbatim. So a `partner_admin` — an org
admin that must NOT sign off examinations — can set its own role, or a new
member's role, to `institution_admin` or `owner`, crossing the very boundary
`domain.INSTITUTION_ADMIN_ROLES` draws, or to an arbitrary undefined string.

These tests assert the *fixed* behaviour and therefore fail until the role is
validated and the granting actor's tier is required to dominate the grant.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.core.auth import Membership
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def _org(client: AsyncClient, make_actor, slug: str = "acme"):  # type: ignore[no-untyped-def]
    root = await make_actor(f"root-{slug}@osceguide.com", platform_admin=True)
    created = await client.post(
        "/api/v1/platform/organizations",
        json={"slug": slug, "name": slug.title(), "org_type": "institution"},
        headers=bearer(root),
    )
    assert created.status_code in (200, 201), created.text
    return uuid.UUID(created.json()["id"])


async def _membership_id(client: AsyncClient, admin: str, slug: str, email: str, role: str) -> str:
    created = await client.post(
        f"/api/v1/orgs/{slug}/memberships",
        json={"email": email, "role": role},
        headers=bearer(admin),
    )
    assert created.status_code in (200, 201), created.text
    return created.json()["id"]


async def test_partner_admin_cannot_grant_institution_admin(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    slug = "acme"
    org_id = await _org(client, make_actor, slug)
    partner = await make_actor(
        f"partner-{slug}@example.com",
        memberships=(Membership(org_id=org_id, org_slug=slug, role="partner_admin"),),
        active_org_slug=slug,
    )
    # A partner admin trying to hand someone the examination-signing role.
    target_id = await _membership_id(client, partner, slug, "victim@example.com", role="trainee")
    response = await client.patch(
        f"/api/v1/orgs/{slug}/memberships/{target_id}",
        json={"role": "institution_admin"},
        headers=bearer(partner),
    )
    assert response.status_code == 403, (
        "a partner_admin must not be able to grant institution_admin; "
        f"got {response.status_code}: {response.text}"
    )


async def test_role_must_be_a_known_value(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    slug = "beta"
    org_id = await _org(client, make_actor, slug)
    admin = await make_actor(
        f"owner-{slug}@example.com",
        memberships=(Membership(org_id=org_id, org_slug=slug, role="owner"),),
        active_org_slug=slug,
    )
    response = await client.post(
        f"/api/v1/orgs/{slug}/memberships",
        json={"email": "new@example.com", "role": "superuser"},
        headers=bearer(admin),
    )
    assert response.status_code in (400, 422), (
        f"an undefined role string must be rejected; got {response.status_code}: {response.text}"
    )
