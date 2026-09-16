"""The station lifecycle over HTTP, and who may drive it."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.core.auth import Membership
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

CONTENT = {"patient_information": {"persona": "anxious"}, "doctor_information": {"task": "assess"}}


async def seed_org(client: AsyncClient, make_actor, slug: str = "kings") -> uuid.UUID:  # type: ignore[no-untyped-def]
    token = await make_actor(f"root-{slug}@osceguide.com", platform_admin=True)
    response = await client.post(
        "/api/v1/platform/organizations",
        json={"slug": slug, "name": slug.title(), "org_type": "institution"},
        headers=bearer(token),
    )
    assert response.status_code == 201, response.text
    return uuid.UUID(response.json()["id"])


async def member(make_actor, org_id: uuid.UUID, slug: str, role: str) -> str:  # type: ignore[no-untyped-def]
    return await make_actor(
        f"{role}-{slug}@example.com",
        memberships=(Membership(org_id=org_id, org_slug=slug, role=role),),
        active_org_slug=slug,
    )


async def make_station(client: AsyncClient, token: str, slug: str = "kings") -> dict:
    response = await client.post(
        f"/api/v1/orgs/{slug}/stations",
        json={"title": "Chest pain", "exam_code": "sca", "content": CONTENT},
        headers=bearer(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


# --------------------------------------------------------------------------
# Authoring
# --------------------------------------------------------------------------


async def test_an_admin_creates_a_station_as_a_draft(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    station = await make_station(client, await member(make_actor, org_id, "kings", "owner"))
    assert station["status"] == "draft"
    assert station["version"] == 1
    assert station["owner_kind"] == "org"


async def test_a_trainee_may_not_author_a_station(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    response = await client.post(
        "/api/v1/orgs/kings/stations",
        json={"title": "Chest pain", "exam_code": "sca", "content": CONTENT},
        headers=bearer(await member(make_actor, org_id, "kings", "trainee")),
    )
    assert response.status_code == 403


async def test_a_station_needs_a_known_exam(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    response = await client.post(
        "/api/v1/orgs/kings/stations",
        json={"title": "X", "exam_code": "mrcp", "content": CONTENT},
        headers=bearer(await member(make_actor, org_id, "kings", "owner")),
    )
    assert response.status_code == 404
    assert response.json()["code"] == "unknown_exam"


# --------------------------------------------------------------------------
# Publishing
# --------------------------------------------------------------------------


async def test_publishing_a_draft_makes_it_usable(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    token = await member(make_actor, org_id, "kings", "owner")
    station = await make_station(client, token)
    response = await client.post(
        f"/api/v1/orgs/kings/stations/{station['id']}/versions/1/publish", headers=bearer(token)
    )
    assert response.status_code == 200
    assert response.json()["status"] == "published"


async def test_publishing_twice_conflicts(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    token = await member(make_actor, org_id, "kings", "owner")
    station = await make_station(client, token)
    url = f"/api/v1/orgs/kings/stations/{station['id']}/versions/1/publish"
    await client.post(url, headers=bearer(token))
    response = await client.post(url, headers=bearer(token))
    assert response.status_code == 409
    assert response.json()["code"] == "already_published"


async def test_a_published_version_cannot_be_edited(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """It is what past attempts were assessed against."""
    org_id = await seed_org(client, make_actor)
    token = await member(make_actor, org_id, "kings", "owner")
    station = await make_station(client, token)
    await client.post(
        f"/api/v1/orgs/kings/stations/{station['id']}/versions/1/publish", headers=bearer(token)
    )
    response = await client.patch(
        f"/api/v1/orgs/kings/stations/{station['id']}/versions/1",
        json={"content": {"changed": True}},
        headers=bearer(token),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "not_editable"


async def test_a_draft_may_be_edited(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    token = await member(make_actor, org_id, "kings", "owner")
    station = await make_station(client, token)
    response = await client.patch(
        f"/api/v1/orgs/kings/stations/{station['id']}/versions/1",
        json={"content": {"patient_information": {"persona": "calm"}}},
        headers=bearer(token),
    )
    assert response.status_code == 200


async def test_a_new_version_is_seeded_from_the_published_one(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    token = await member(make_actor, org_id, "kings", "owner")
    station = await make_station(client, token)
    await client.post(
        f"/api/v1/orgs/kings/stations/{station['id']}/versions/1/publish", headers=bearer(token)
    )
    response = await client.post(
        f"/api/v1/orgs/kings/stations/{station['id']}/versions", headers=bearer(token)
    )
    assert response.status_code == 201
    assert response.json()["version"] == 2
    assert response.json()["status"] == "draft"
    assert response.json()["content"] == CONTENT


async def test_archiving_needs_a_published_version(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    token = await member(make_actor, org_id, "kings", "owner")
    station = await make_station(client, token)
    response = await client.post(
        f"/api/v1/orgs/kings/stations/{station['id']}/versions/1/archive", headers=bearer(token)
    )
    assert response.status_code == 409
    assert response.json()["code"] == "not_archivable"


# --------------------------------------------------------------------------
# Listing and isolation
# --------------------------------------------------------------------------


async def test_an_org_sees_its_own_stations(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    token = await member(make_actor, org_id, "kings", "owner")
    await make_station(client, token)
    response = await client.get("/api/v1/orgs/kings/stations", headers=bearer(token))
    assert response.status_code == 200
    assert [s["title"] for s in response.json()["items"]] == ["Chest pain"]


async def test_another_orgs_stations_are_invisible(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    kings = await seed_org(client, make_actor, "kings")
    guys = await seed_org(client, make_actor, "guys")
    await make_station(client, await member(make_actor, kings, "kings", "owner"))
    response = await client.get(
        "/api/v1/orgs/guys/stations", headers=bearer(await member(make_actor, guys, "guys", "owner"))
    )
    assert response.json()["items"] == []


async def test_a_trainee_may_browse_stations(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    await make_station(client, await member(make_actor, org_id, "kings", "owner"))
    response = await client.get(
        "/api/v1/orgs/kings/stations",
        headers=bearer(await member(make_actor, org_id, "kings", "trainee")),
    )
    assert response.status_code == 200
