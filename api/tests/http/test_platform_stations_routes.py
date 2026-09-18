"""The platform authors its own library, through the same routes an org uses.

Until now the platform half of `stations` had no write path at all: the library
came from a legacy import or a hand-written row, and the shape of each exam's
stations lived in the engine as a formatter chosen by a branch on the exam's
code. These pin the two directions that matter — an org may build on what the
platform publishes, and neither side may author the other's content.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.core.auth import Membership
from tests.support.catalog import create_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

# A template whose blocks say what each is for. `role` is what the renderer
# places them by, which is what replaced the per-exam formatters.
TEMPLATE = {
    "blocks": [
        {"id": "who_you_are", "label": "Who you are", "kind": "text", "role": "persona"},
        {"id": "why_you_came", "label": "Why you came", "kind": "text", "role": "complaint"},
        {"id": "expected_answers", "label": "Expected answers", "kind": "text", "role": "examiner"},
    ],
    "layout": {"persona": "patient"},
}

CONTENT = {
    "who_you_are": "Marek, 61, retired bus driver.",
    "why_you_came": "Short of breath walking to the shops.",
    "expected_answers": "Elicits the smoking history and offers cessation support.",
}


async def admin_token(make_actor) -> str:  # type: ignore[no-untyped-def]
    return await make_actor("admin@osceguide.com", platform_admin=True)


async def an_org(client: AsyncClient, make_actor, slug: str = "kings") -> uuid.UUID:  # type: ignore[no-untyped-def]
    root = await make_actor(f"root-{slug}@osceguide.com", platform_admin=True)
    response = await client.post(
        "/api/v1/platform/organizations",
        json={"slug": slug, "name": slug.title(), "org_type": "institution"},
        headers=bearer(root),
    )
    assert response.status_code == 201, response.text
    return uuid.UUID(response.json()["id"])


async def org_admin(make_actor, org_id: uuid.UUID, slug: str = "kings") -> str:  # type: ignore[no-untyped-def]
    return await make_actor(
        f"admin-{slug}@example.com",
        memberships=(Membership(org_id=org_id, org_slug=slug, role="admin"),),
        active_org_slug=slug,
    )


async def a_platform_template(client: AsyncClient, admin: str) -> str:
    created = await client.post(
        "/api/v1/platform/station-templates",
        json={"title": "Consultation", "exam_code": "sca", "structure": TEMPLATE},
        headers=bearer(admin),
    )
    assert created.status_code == 201, created.text
    published = await client.post(
        f"/api/v1/platform/station-templates/{created.json()['id']}/publish", headers=bearer(admin)
    )
    assert published.status_code == 200, published.text
    return str(published.json()["id"])


async def test_a_platform_admin_authors_and_publishes_a_library_station(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    admin = await admin_token(make_actor)
    await create_exam(client, admin, code="sca")
    template_version_id = await a_platform_template(client, admin)

    created = await client.post(
        "/api/v1/platform/stations",
        json={
            "title": "COPD exacerbation",
            "exam_code": "sca",
            "content": CONTENT,
            "template_version_id": template_version_id,
        },
        headers=bearer(admin),
    )
    assert created.status_code == 201, created.text
    assert created.json()["owner_kind"] == "platform"

    published = await client.post(
        f"/api/v1/platform/stations/{created.json()['id']}/versions/1/publish", headers=bearer(admin)
    )
    assert published.status_code == 200, published.text

    # And it is in the library every organisation draws on.
    library = await client.get("/api/v1/stations", headers=bearer(await make_actor("t@example.com")))
    assert [s["title"] for s in library.json()["items"]] == ["COPD exacerbation"]


async def test_a_draft_library_station_is_not_in_the_library(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await admin_token(make_actor)
    await create_exam(client, admin, code="sca")
    await client.post(
        "/api/v1/platform/stations",
        json={"title": "Half written", "exam_code": "sca", "content": CONTENT},
        headers=bearer(admin),
    )

    library = await client.get("/api/v1/stations", headers=bearer(await make_actor("t@example.com")))
    mine = await client.get("/api/v1/platform/stations", headers=bearer(admin))

    assert library.json()["items"] == []
    assert [s["title"] for s in mine.json()["items"]] == ["Half written"], "its author still sees it"


async def test_an_org_admin_cannot_write_the_library(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await an_org(client, make_actor)
    response = await client.post(
        "/api/v1/platform/stations",
        json={"title": "Ours now", "exam_code": "sca", "content": CONTENT},
        headers=bearer(await org_admin(make_actor, org_id)),
    )
    assert response.status_code == 403


async def test_an_org_builds_its_own_station_on_a_platform_template(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The shape is shared downward; the content stays the institution's own."""
    admin = await admin_token(make_actor)
    await create_exam(client, admin, code="sca")
    template_version_id = await a_platform_template(client, admin)
    org_id = await an_org(client, make_actor)

    response = await client.post(
        "/api/v1/orgs/kings/stations",
        json={
            "title": "Our own case",
            "exam_code": "sca",
            "content": CONTENT,
            "template_version_id": template_version_id,
        },
        headers=bearer(await org_admin(make_actor, org_id)),
    )

    assert response.status_code == 201, response.text
    assert response.json()["owner_kind"] == "org"


async def test_an_org_cannot_edit_a_platform_template(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await admin_token(make_actor)
    await create_exam(client, admin, code="sca")
    created = await client.post(
        "/api/v1/platform/station-templates",
        json={"title": "Consultation", "exam_code": "sca", "structure": TEMPLATE},
        headers=bearer(admin),
    )
    org_id = await an_org(client, make_actor)

    response = await client.patch(
        f"/api/v1/orgs/kings/station-templates/{created.json()['id']}/versions/1",
        json={"structure": {"blocks": []}},
        headers=bearer(await org_admin(make_actor, org_id)),
    )

    assert response.status_code == 404


async def test_a_platform_admin_is_not_thereby_an_org_admin(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Deliberate: `OrgAdmin` sets allow_platform_admin=False."""
    await an_org(client, make_actor)  # the org exists; the admin still is not its admin
    admin = await admin_token(make_actor)
    await create_exam(client, admin, code="sca")

    response = await client.post(
        "/api/v1/orgs/kings/stations",
        json={"title": "Theirs now", "exam_code": "sca", "content": CONTENT},
        headers=bearer(admin),
    )

    assert response.status_code == 403
