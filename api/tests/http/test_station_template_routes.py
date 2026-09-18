"""Station templates: the shape an organisation's stations take.

The tables were modelled and had no repository, no service and no routes, so
`station_versions.template_version_id` could only ever be null and T3 — a
station may only be built on a *published* template — had nothing to refuse.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.core.auth import Membership
from tests.support.catalog import create_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

STRUCTURE = {"fields": ["patient_information", "doctor_information"]}
CONTENT = {"patient_information": {"persona": "anxious"}}


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


async def a_template(client: AsyncClient, admin: str, slug: str = "kings") -> dict:
    created = await client.post(
        f"/api/v1/orgs/{slug}/station-templates",
        json={"title": "SCA consultation", "exam_code": "sca", "structure": STRUCTURE},
        headers=bearer(admin),
    )
    assert created.status_code == 201, created.text
    return created.json()


async def test_a_template_is_created_with_a_first_draft(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    template = await a_template(client, admin)

    assert template["title"] == "SCA consultation"
    assert template["exam_code"] == "sca"
    assert [v["version"] for v in template["versions"]] == [1]
    assert template["versions"][0]["status"] == "draft"


async def test_a_template_is_listed(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    await a_template(client, admin)

    listed = await client.get("/api/v1/orgs/kings/station-templates", headers=bearer(admin))
    assert listed.status_code == 200
    assert [t["title"] for t in listed.json()["items"]] == ["SCA consultation"]


async def test_a_published_version_is_not_editable(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    template = await a_template(client, admin)
    published = await client.post(
        f"/api/v1/orgs/kings/station-templates/{template['id']}/publish", headers=bearer(admin)
    )
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "published"

    refused = await client.patch(
        f"/api/v1/orgs/kings/station-templates/{template['id']}/versions/1",
        json={"structure": {"fields": []}},
        headers=bearer(admin),
    )
    assert refused.status_code == 409
    assert refused.json()["code"] == "not_editable"


async def test_a_new_draft_is_seeded_from_the_published_version(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    template = await a_template(client, admin)
    await client.post(f"/api/v1/orgs/kings/station-templates/{template['id']}/publish", headers=bearer(admin))

    draft = await client.post(
        f"/api/v1/orgs/kings/station-templates/{template['id']}/versions", headers=bearer(admin)
    )
    assert draft.status_code == 201, draft.text
    assert draft.json()["version"] == 2
    assert draft.json()["status"] == "draft"
    assert draft.json()["structure"] == STRUCTURE


async def test_a_station_can_be_built_on_a_published_template(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    template = await a_template(client, admin)
    published = await client.post(
        f"/api/v1/orgs/kings/station-templates/{template['id']}/publish", headers=bearer(admin)
    )

    station = await client.post(
        "/api/v1/orgs/kings/stations",
        json={
            "title": "Chest pain",
            "exam_code": "sca",
            "content": CONTENT,
            "template_version_id": published.json()["id"],
        },
        headers=bearer(admin),
    )
    assert station.status_code == 201, station.text


async def test_a_station_cannot_be_built_on_a_draft_template(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """T3, which had nothing to refuse until these routes existed.

    A station built on a shape somebody is still deciding would change under
    it — and an attempt is supposed to be frozen against what it was assessed
    on.
    """
    org_id, admin = await org_with_admin(client, make_actor)
    template = await a_template(client, admin)

    station = await client.post(
        "/api/v1/orgs/kings/stations",
        json={
            "title": "Chest pain",
            "exam_code": "sca",
            "content": CONTENT,
            "template_version_id": template["versions"][0]["id"],
        },
        headers=bearer(admin),
    )
    assert station.status_code == 409
    assert station.json()["code"] == "template_not_published"


async def test_another_organisations_template_cannot_be_bound(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Indistinguishable from one that does not exist, so ids cannot be probed."""
    org_id, admin = await org_with_admin(client, make_actor)
    _, other_admin = await org_with_admin(client, make_actor, slug="guys")
    template = await a_template(client, other_admin, slug="guys")
    published = await client.post(
        f"/api/v1/orgs/guys/station-templates/{template['id']}/publish", headers=bearer(other_admin)
    )

    station = await client.post(
        "/api/v1/orgs/kings/stations",
        json={
            "title": "Borrowed",
            "exam_code": "sca",
            "content": CONTENT,
            "template_version_id": published.json()["id"],
        },
        headers=bearer(admin),
    )
    assert station.status_code == 404
    assert station.json()["code"] == "station_template_version_not_found"


async def test_a_station_needs_no_template_at_all(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Templates are a convenience for authors, not a gate on authoring."""
    org_id, admin = await org_with_admin(client, make_actor)
    station = await client.post(
        "/api/v1/orgs/kings/stations",
        json={"title": "Freehand", "exam_code": "sca", "content": CONTENT},
        headers=bearer(admin),
    )
    assert station.status_code == 201, station.text


async def test_templates_are_refused_to_outsiders(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    await org_with_admin(client, make_actor)
    stranger = await make_actor("nobody@example.com")
    response = await client.get("/api/v1/orgs/kings/station-templates", headers=bearer(stranger))
    assert response.status_code == 403
