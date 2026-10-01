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

STRUCTURE = {
    "schemaVersion": 1,
    "sections": [
        {
            "id": "main",
            "title": "Main",
            "blocks": [
                {"id": "patient_information", "type": "longText", "label": "Patient information"},
                {"id": "doctor_information", "type": "longText", "label": "Doctor information"},
            ],
        }
    ],
}
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


async def test_renaming_a_draft_is_what_the_list_reads_back(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The editor used to validate a new title and then save the structure alone."""
    org_id, admin = await org_with_admin(client, make_actor)
    template = await a_template(client, admin)

    renamed = await client.patch(
        f"/api/v1/orgs/kings/station-templates/{template['id']}/versions/1",
        json={"structure": STRUCTURE, "title": "  Chest pain  "},
        headers=bearer(admin),
    )
    assert renamed.status_code == 200, renamed.text

    listed = await client.get("/api/v1/orgs/kings/station-templates", headers=bearer(admin))
    assert listed.status_code == 200
    assert [t["title"] for t in listed.json()["items"]] == ["Chest pain"]

    blank = await client.patch(
        f"/api/v1/orgs/kings/station-templates/{template['id']}/versions/1",
        json={"structure": STRUCTURE, "title": "   "},
        headers=bearer(admin),
    )
    assert blank.status_code == 422


async def test_a_template_is_listed(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    await a_template(client, admin)

    listed = await client.get("/api/v1/orgs/kings/station-templates", headers=bearer(admin))
    assert listed.status_code == 200
    assert [t["title"] for t in listed.json()["items"]] == ["SCA consultation"]


async def test_templates_are_filtered_by_search_exam_and_published(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    root = await make_actor("root2-kings@osceguide.com", platform_admin=True)
    await create_exam(client, root, code="casc")

    sca_template = await a_template(client, admin)  # "SCA consultation", exam_code sca
    await client.post(
        f"/api/v1/orgs/kings/station-templates/{sca_template['id']}/publish", headers=bearer(admin)
    )
    casc_template = await client.post(
        "/api/v1/orgs/kings/station-templates",
        json={"title": "CASC role-play", "exam_code": "casc", "structure": STRUCTURE},
        headers=bearer(admin),
    )
    assert casc_template.status_code == 201, casc_template.text
    unscoped_template = await client.post(
        "/api/v1/orgs/kings/station-templates",
        json={"title": "Generic form", "exam_code": None, "structure": STRUCTURE},
        headers=bearer(admin),
    )
    assert unscoped_template.status_code == 201, unscoped_template.text

    # `search` matches a title fragment.
    searched = await client.get(
        "/api/v1/orgs/kings/station-templates", params={"search": "consult"}, headers=bearer(admin)
    )
    assert [t["title"] for t in searched.json()["items"]] == ["SCA consultation"]

    # `exam_code` matches that exam plus every exam-agnostic template.
    scoped = await client.get(
        "/api/v1/orgs/kings/station-templates", params={"exam_code": "sca"}, headers=bearer(admin)
    )
    assert {t["title"] for t in scoped.json()["items"]} == {"SCA consultation", "Generic form"}

    # `published_only` keeps only the template with a published version.
    published = await client.get(
        "/api/v1/orgs/kings/station-templates", params={"published_only": "true"}, headers=bearer(admin)
    )
    assert [t["title"] for t in published.json()["items"]] == ["SCA consultation"]


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


async def test_a_draft_template_version_can_be_deleted(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    template = await a_template(client, admin)

    deleted = await client.delete(
        f"/api/v1/orgs/kings/station-templates/{template['id']}/versions/1", headers=bearer(admin)
    )
    assert deleted.status_code == 204, deleted.text

    listed = await client.get("/api/v1/orgs/kings/station-templates", headers=bearer(admin))
    assert listed.status_code == 200
    assert listed.json()["items"] == []


async def test_a_published_template_version_can_be_archived(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    template = await a_template(client, admin)
    await client.post(f"/api/v1/orgs/kings/station-templates/{template['id']}/publish", headers=bearer(admin))

    archived = await client.post(
        f"/api/v1/orgs/kings/station-templates/{template['id']}/versions/1/archive",
        headers=bearer(admin),
    )
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "archived"


async def test_a_published_template_version_cannot_be_deleted(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    template = await a_template(client, admin)
    await client.post(f"/api/v1/orgs/kings/station-templates/{template['id']}/publish", headers=bearer(admin))

    response = await client.delete(
        f"/api/v1/orgs/kings/station-templates/{template['id']}/versions/1", headers=bearer(admin)
    )
    assert response.status_code == 409
    assert response.json()["code"] == "not_deletable"


async def test_templates_are_listed_a_page_at_a_time(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The cursor used to be always empty, so a long list could not be paged."""
    org_id, admin = await org_with_admin(client, make_actor)
    created_ids = {(await a_template(client, admin))["id"] for _ in range(3)}

    first = await client.get(
        "/api/v1/orgs/kings/station-templates", params={"limit": 2}, headers=bearer(admin)
    )
    assert first.status_code == 200, first.text
    assert len(first.json()["items"]) == 2
    assert first.json()["next_cursor"] is not None

    rest = await client.get(
        "/api/v1/orgs/kings/station-templates",
        params={"limit": 2, "cursor": first.json()["next_cursor"]},
        headers=bearer(admin),
    )
    assert rest.json()["next_cursor"] is None
    listed_ids = [template["id"] for template in first.json()["items"] + rest.json()["items"]]
    assert sorted(listed_ids) == sorted(created_ids)


async def test_a_platform_template_is_copied_into_the_organisation_published(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    root = await make_actor("root3-kings@osceguide.com", platform_admin=True)
    standard = await client.post(
        "/api/v1/platform/station-templates",
        json={"title": "Simulation scenario", "structure": STRUCTURE},
        headers=bearer(root),
    )
    assert standard.status_code == 201, standard.text
    source_id = standard.json()["id"]

    published = await client.post(
        f"/api/v1/platform/station-templates/{source_id}/publish", headers=bearer(root)
    )
    assert published.status_code == 200, published.text

    copied = await client.post(
        f"/api/v1/orgs/kings/station-templates/{source_id}/copy", headers=bearer(admin)
    )
    assert copied.status_code == 201, copied.text
    copy = copied.json()
    assert copy["id"] != source_id
    assert copy["title"] == "Simulation scenario"
    assert copy["exam_code"] is None
    assert [(version["version"], version["status"]) for version in copy["versions"]] == [(1, "published")]
    assert copy["versions"][0]["structure"] == STRUCTURE

    # The copy is the organisation's own: it can start a new draft of it, which it cannot of the platform's.
    own_draft = await client.post(
        f"/api/v1/orgs/kings/station-templates/{copy['id']}/versions", headers=bearer(admin)
    )
    assert own_draft.status_code == 201, own_draft.text
    platform_draft = await client.post(
        f"/api/v1/orgs/kings/station-templates/{source_id}/versions", headers=bearer(admin)
    )
    assert platform_draft.status_code == 404, platform_draft.text


async def test_an_organisations_own_template_is_not_a_platform_template_to_copy(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    own = await a_template(client, admin)
    refused = await client.post(
        f"/api/v1/orgs/kings/station-templates/{own['id']}/copy", headers=bearer(admin)
    )
    assert refused.status_code == 404, refused.text


async def test_a_platform_template_that_is_still_a_draft_cannot_be_copied(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    root = await make_actor("root3-kings@osceguide.com", platform_admin=True)
    draft = await client.post(
        "/api/v1/platform/station-templates",
        json={"title": "Simulation scenario", "structure": STRUCTURE},
        headers=bearer(root),
    )
    refused = await client.post(
        f"/api/v1/orgs/kings/station-templates/{draft.json()['id']}/copy", headers=bearer(admin)
    )
    assert refused.status_code == 409, refused.text
    assert refused.json()["code"] == "template_not_published"
