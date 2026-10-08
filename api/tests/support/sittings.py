"""Helpers for scheduling sittings after the rubric-only binding change."""

from __future__ import annotations

import uuid

from httpx import AsyncClient

from app.core.auth import Membership
from tests.support.catalog import create_exam
from tests.support.tokens import bearer


async def org_with_admin(client: AsyncClient, make_actor, slug: str = "kings"):  # type: ignore[no-untyped-def]
    """An institution organisation and its owner token, with the `sca` exam written."""
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
    # first, by a platform admin, which is exactly who is holding this token.
    await create_exam(client, root, code="sca")
    return org_id, admin


async def add_programme(
    client: AsyncClient, admin_token: str, *, org_slug: str, exam_code: str = "sca", active: bool = True
) -> uuid.UUID:
    """A programme, activated unless `active=False`: a draft is not offered (B-3)."""
    response = await client.post(
        f"/api/v1/orgs/{org_slug}/programmes",
        json={"exam_code": exam_code},
        headers=bearer(admin_token),
    )
    assert response.status_code == 201, response.text
    programme_id = uuid.UUID(response.json()["id"])
    if active:
        activated = await client.patch(
            f"/api/v1/orgs/{org_slug}/programmes/{programme_id}",
            json={"status": "active"},
            headers=bearer(admin_token),
        )
        assert activated.status_code == 200, activated.text
    return programme_id


def create_sitting_body(
    *,
    name: str,
    programme_id: uuid.UUID,
    mode: str = "exam",
    sitting_type: str = "group_training",
) -> dict[str, str]:
    return {
        "name": name,
        "programme_id": str(programme_id),
        "mode": mode,
        "sitting_type": sitting_type,
    }
