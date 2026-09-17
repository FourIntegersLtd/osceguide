"""Authoring the rubric a sitting binds.

`FeedbackTemplateVersion` had a model, one read and no write path: every test
inserted the row by hand, and no organisation could create a sitting through
the API. These are the routes that make the institutional product reachable.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.core.auth import Membership
from tests.support.rubrics import create_rubric, rubric_with_domains
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

DOMAINS = {"domains": ["communication", "data_gathering", "clinical_analysis"]}


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
    return org_id, admin


async def publish(client: AsyncClient, admin: str, template_id: str, slug: str = "kings") -> dict:
    response = await client.post(
        f"/api/v1/orgs/{slug}/feedback-templates/{template_id}/publish", headers=bearer(admin)
    )
    assert response.status_code == 200, response.text
    return response.json()


async def create_template(client: AsyncClient, admin: str, slug: str = "kings", **body: object) -> dict:
    # A template narrows a rubric, so one has to exist; the selection is checked
    # against its domains, which is what naming an exam code could never do.
    if "rubric_version_id" not in body:
        rubric = await create_rubric(
            client, admin, org_slug=slug, structure=rubric_with_domains("communication", "data_gathering")
        )
        body = {"rubric_version_id": rubric["version_id"], **body}
    payload = {"title": "Finals rubric", "field_selection": DOMAINS, **body}
    response = await client.post(
        f"/api/v1/orgs/{slug}/feedback-templates", json=payload, headers=bearer(admin)
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_a_template_starts_as_a_draft_and_publishes(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    template = await create_template(client, admin)
    assert template["owner_kind"] == "org"
    assert [v["version"] for v in template["versions"]] == [1]
    assert template["versions"][0]["status"] == "draft"

    published = await client.post(
        f"/api/v1/orgs/kings/feedback-templates/{template['id']}/publish", headers=bearer(admin)
    )
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "published"
    assert published.json()["published_at"] is not None

    listed = await client.get("/api/v1/orgs/kings/feedback-templates", headers=bearer(admin))
    assert [t["title"] for t in listed.json()["items"]] == ["Finals rubric"]
    assert listed.json()["items"][0]["versions"][0]["status"] == "published"


async def test_a_published_template_binds_a_sitting(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The whole point: S1 satisfied over HTTP, with no row inserted by hand."""
    _, admin = await org_with_admin(client, make_actor)
    template = await create_template(client, admin)
    version = (
        await client.post(
            f"/api/v1/orgs/kings/feedback-templates/{template['id']}/publish", headers=bearer(admin)
        )
    ).json()

    sitting = await client.post(
        "/api/v1/orgs/kings/sittings",
        json={"name": "Finals", "feedback_template_version_id": version["id"], "mode": "exam"},
        headers=bearer(admin),
    )
    assert sitting.status_code == 201, sitting.text


async def test_a_published_version_cannot_be_edited(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    template = await create_template(client, admin)
    await client.post(
        f"/api/v1/orgs/kings/feedback-templates/{template['id']}/publish", headers=bearer(admin)
    )

    edited = await client.patch(
        f"/api/v1/orgs/kings/feedback-templates/{template['id']}/versions/1",
        json={"field_selection": {"domains": ["communication"]}},
        headers=bearer(admin),
    )
    assert edited.status_code == 409
    assert edited.json()["code"] == "not_editable"


async def test_publishing_twice_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    template = await create_template(client, admin)
    url = f"/api/v1/orgs/kings/feedback-templates/{template['id']}/publish"
    await client.post(url, headers=bearer(admin))
    again = await client.post(url, headers=bearer(admin))
    assert again.status_code == 409
    assert again.json()["code"] == "already_published"


async def test_a_new_version_is_seeded_from_the_published_one(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    template = await create_template(client, admin)
    await client.post(
        f"/api/v1/orgs/kings/feedback-templates/{template['id']}/publish", headers=bearer(admin)
    )

    draft = await client.post(
        f"/api/v1/orgs/kings/feedback-templates/{template['id']}/versions", headers=bearer(admin)
    )
    assert draft.status_code == 201, draft.text
    assert draft.json()["version"] == 2
    assert draft.json()["status"] == "draft"
    assert draft.json()["field_selection"] == DOMAINS

    edited = await client.patch(
        f"/api/v1/orgs/kings/feedback-templates/{template['id']}/versions/2",
        json={"field_selection": {"domains": ["communication"]}},
        headers=bearer(admin),
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["field_selection"] == {"domains": ["communication"]}


async def test_another_orgs_template_is_invisible(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, kings_admin = await org_with_admin(client, make_actor, "kings")
    _, guys_admin = await org_with_admin(client, make_actor, "guys")
    template = await create_template(client, kings_admin)

    response = await client.post(
        f"/api/v1/orgs/guys/feedback-templates/{template['id']}/publish", headers=bearer(guys_admin)
    )
    assert response.status_code == 404
    assert response.json()["code"] == "feedback_template_not_found"

    listed = await client.get("/api/v1/orgs/guys/feedback-templates", headers=bearer(guys_admin))
    assert listed.json()["items"] == []


async def test_only_an_org_admin_may_author(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id, _ = await org_with_admin(client, make_actor)
    trainee = await make_actor(
        "trainee-kings@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="trainee"),),
        active_org_slug="kings",
    )
    response = await client.post(
        "/api/v1/orgs/kings/feedback-templates",
        json={"title": "Mine", "field_selection": {}},
        headers=bearer(trainee),
    )
    assert response.status_code == 403


async def test_a_template_must_narrow_a_rubric_that_exists(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """It named an exam before, which said nothing about what it selects from."""
    _, admin = await org_with_admin(client, make_actor)
    response = await client.post(
        "/api/v1/orgs/kings/feedback-templates",
        json={
            "title": "Odd",
            "rubric_version_id": "11111111-1111-1111-1111-111111111111",
            "field_selection": {},
        },
        headers=bearer(admin),
    )
    assert response.status_code == 404
    assert response.json()["code"] == "rubric_version_not_found"


async def test_a_selection_outside_the_rubric_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Nothing checked this before: a template could name a domain no schema had,
    and every review built on it was impossible to complete."""
    _, admin = await org_with_admin(client, make_actor)
    rubric = await create_rubric(
        client, admin, org_slug="kings", structure=rubric_with_domains("communication")
    )
    response = await client.post(
        "/api/v1/orgs/kings/feedback-templates",
        json={
            "title": "Odd",
            "rubric_version_id": rubric["version_id"],
            "field_selection": {"domains": ["invented"]},
        },
        headers=bearer(admin),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_rubric"


async def test_a_draft_rubric_cannot_be_narrowed(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    rubric = await create_rubric(client, admin, org_slug="kings", publish=False)
    response = await client.post(
        "/api/v1/orgs/kings/feedback-templates",
        json={"title": "Odd", "rubric_version_id": rubric["version_id"], "field_selection": {}},
        headers=bearer(admin),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "rubric_version_not_published"
