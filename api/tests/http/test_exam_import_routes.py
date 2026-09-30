"""An organisation adopting a platform exam by reference: the catalogue it chooses from, and the import.

Nothing is copied. An import is an `org_programmes` row naming the platform exam, which is
what makes it show in the organisation's exams, runnable in a sitting and grantable as
practice access.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from tests.http.test_stations_routes import a_library_station
from tests.support.catalog import create_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def organisation_with_admin(client: AsyncClient, make_actor, slug: str = "kings"):  # type: ignore[no-untyped-def]
    """An organisation, its owner's token and the platform admin's token."""
    root = await make_actor(f"root-{slug}@osceguide.com", platform_admin=True)
    created = await client.post(
        "/api/v1/platform/organizations",
        json={"slug": slug, "name": f"{slug.title()} Medical School", "org_type": "institution"},
        headers=bearer(root),
    )
    assert created.status_code == 201, created.text
    admin = await make_actor(
        f"admin-{slug}@example.com",
        memberships=(Membership(org_id=uuid.UUID(created.json()["id"]), org_slug=slug, role="owner"),),
        active_org_slug=slug,
    )
    return admin, root


async def test_the_catalogue_lists_published_platform_exams_with_station_counts(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    admin, root = await organisation_with_admin(client, make_actor)
    plab = await create_exam(client, root, code="plab", name="PLAB 2")
    casc = await create_exam(client, root, code="casc", name="CASC")
    await create_exam(client, root, code="ortho", publish=False)
    await a_library_station(db_session, "Chest pain", exam_code="plab")
    await a_library_station(db_session, "Breathlessness", exam_code="plab")

    catalogue = await client.get("/api/v1/orgs/kings/exams/catalog", headers=bearer(admin))
    assert catalogue.status_code == 200, catalogue.text
    assert sorted(catalogue.json()["items"], key=lambda item: item["code"]) == [
        {
            "exam_id": casc["id"],
            "code": "casc",
            "title": "CASC",
            "station_count": 0,
            "already_imported": False,
        },
        {
            "exam_id": plab["id"],
            "code": "plab",
            "title": "PLAB 2",
            "station_count": 2,
            "already_imported": False,
        },
    ]

    imported = await client.post(
        "/api/v1/orgs/kings/exams/import", json={"platform_exam_id": plab["id"]}, headers=bearer(admin)
    )
    assert imported.status_code == 201, imported.text
    exam = imported.json()["exam"]
    assert (exam["id"], exam["code"], exam["name"], exam["status"]) == (
        plab["id"],
        "plab",
        "PLAB 2",
        "published",
    )

    after = (await client.get("/api/v1/orgs/kings/exams/catalog", headers=bearer(admin))).json()["items"]
    assert {item["code"]: item["already_imported"] for item in after} == {"casc": False, "plab": True}


async def test_an_imported_exam_is_the_organisations_to_run(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin, root = await organisation_with_admin(client, make_actor)
    plab = await create_exam(client, root, code="plab", name="PLAB 2")
    await client.post(
        "/api/v1/orgs/kings/exams/import", json={"platform_exam_id": plab["id"]}, headers=bearer(admin)
    )

    exams = (await client.get("/api/v1/orgs/kings/exams", headers=bearer(admin))).json()["items"]
    assert plab["id"] in [exam["id"] for exam in exams]
    programmes = (await client.get("/api/v1/orgs/kings/programmes", headers=bearer(admin))).json()["items"]
    assert [(row["exam_id"], row["source"], row["status"]) for row in programmes] == [
        (plab["id"], "imported_osce_guide", "active")
    ]

    granted = await client.post(
        "/api/v1/orgs/kings/practice-access",
        json={"email": "trainee@example.com", "exam_id": plab["id"]},
        headers=bearer(admin),
    )
    assert granted.status_code == 201, granted.text
    assert granted.json()["item"]["exam_code"] == "plab"

    # Importing it again is a conflict, and changes nothing.
    again = await client.post(
        "/api/v1/orgs/kings/exams/import", json={"platform_exam_id": plab["id"]}, headers=bearer(admin)
    )
    assert again.status_code == 409
    assert again.json()["code"] == "exam_already_imported"


async def test_only_a_published_platform_exam_can_be_imported(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin, root = await organisation_with_admin(client, make_actor)
    draft = await create_exam(client, root, code="ortho", publish=False)
    for platform_exam_id in (draft["id"], str(uuid.uuid4())):
        refused = await client.post(
            "/api/v1/orgs/kings/exams/import",
            json={"platform_exam_id": platform_exam_id},
            headers=bearer(admin),
        )
        assert refused.status_code == 404, platform_exam_id
        assert refused.json()["code"] == "unknown_exam"


async def test_another_organisations_own_exam_cannot_be_imported(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin, root = await organisation_with_admin(client, make_actor)
    rival_admin, _ = await organisation_with_admin(client, make_actor, slug="rival")
    plab = await create_exam(client, root, code="plab")
    own = await client.post(
        "/api/v1/orgs/rival/exams",
        json={
            "code": "finals",
            "name": "Rival finals",
            "default_reading_seconds": 90,
            "default_simulation_seconds": 600,
            "rubric_version_id": plab["rubric_version_id"],
        },
        headers=bearer(rival_admin),
    )
    assert own.status_code == 201, own.text
    rival_exam_id = own.json()["id"]
    published = await client.post(
        f"/api/v1/orgs/rival/exams/{rival_exam_id}/publish", headers=bearer(rival_admin)
    )
    assert published.status_code == 200, published.text

    catalogue = (await client.get("/api/v1/orgs/kings/exams/catalog", headers=bearer(admin))).json()["items"]
    assert [item["code"] for item in catalogue] == ["plab"]
    refused = await client.post(
        "/api/v1/orgs/kings/exams/import", json={"platform_exam_id": rival_exam_id}, headers=bearer(admin)
    )
    assert refused.status_code == 404
    assert refused.json()["code"] == "unknown_exam"


async def test_importing_needs_an_administrator_of_that_organisation(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, root = await organisation_with_admin(client, make_actor)
    rival_admin, _ = await organisation_with_admin(client, make_actor, slug="rival")
    plab = await create_exam(client, root, code="plab")
    foreign = await client.post(
        "/api/v1/orgs/kings/exams/import", json={"platform_exam_id": plab["id"]}, headers=bearer(rival_admin)
    )
    assert foreign.status_code == 403
    foreign_catalogue = await client.get("/api/v1/orgs/kings/exams/catalog", headers=bearer(rival_admin))
    assert foreign_catalogue.status_code == 403
