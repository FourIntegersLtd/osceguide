"""Exams are read-only; programmes are an organisation's own."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.core.auth import Membership
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


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


async def test_the_four_exams_are_served(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    response = await client.get("/api/v1/exams", headers=bearer(await make_actor()))
    assert response.status_code == 200
    assert {e["code"] for e in response.json()["items"]} == {"sca", "plab", "casc", "ortho"}


async def test_an_exam_carries_its_framework_and_timings(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    response = await client.get("/api/v1/exams", headers=bearer(await make_actor()))
    sca = next(e for e in response.json()["items"] if e["code"] == "sca")
    assert sca["framework_id"] == "sca-rcgp-v1"
    assert sca["default_simulation_seconds"] == 900


async def test_an_org_admin_adds_a_programme(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    response = await client.post(
        "/api/v1/orgs/kings/programmes",
        json={"exam_code": "plab"},
        headers=bearer(await member(make_actor, org_id, "kings", "owner")),
    )
    assert response.status_code == 201
    assert response.json()["exam_code"] == "plab"
    assert response.json()["status"] == "draft"


async def test_adding_the_same_programme_twice_conflicts(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    token = await member(make_actor, org_id, "kings", "owner")
    await client.post("/api/v1/orgs/kings/programmes", json={"exam_code": "plab"}, headers=bearer(token))
    response = await client.post(
        "/api/v1/orgs/kings/programmes", json={"exam_code": "plab"}, headers=bearer(token)
    )
    assert response.status_code == 409
    assert response.json()["code"] == "programme_exists"


async def test_an_unknown_exam_is_refused_rather_than_defaulted(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """b2c defaulted an unrecognised app_type to sca. That is how CASC ended up
    marked with a GP rubric, so this refuses instead."""
    org_id = await seed_org(client, make_actor)
    response = await client.post(
        "/api/v1/orgs/kings/programmes",
        json={"exam_code": "mrcp"},
        headers=bearer(await member(make_actor, org_id, "kings", "owner")),
    )
    assert response.status_code == 404
    assert response.json()["code"] == "unknown_exam"


async def test_a_trainee_may_not_add_a_programme(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    response = await client.post(
        "/api/v1/orgs/kings/programmes",
        json={"exam_code": "plab"},
        headers=bearer(await member(make_actor, org_id, "kings", "trainee")),
    )
    assert response.status_code == 403


async def test_a_trainee_may_read_the_programmes(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    await client.post(
        "/api/v1/orgs/kings/programmes",
        json={"exam_code": "sca"},
        headers=bearer(await member(make_actor, org_id, "kings", "owner")),
    )
    response = await client.get(
        "/api/v1/orgs/kings/programmes",
        headers=bearer(await member(make_actor, org_id, "kings", "trainee")),
    )
    assert response.status_code == 200
    assert [p["exam_code"] for p in response.json()["items"]] == ["sca"]


async def test_another_orgs_programmes_are_invisible(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    kings = await seed_org(client, make_actor, "kings")
    guys = await seed_org(client, make_actor, "guys")
    await client.post(
        "/api/v1/orgs/kings/programmes",
        json={"exam_code": "sca"},
        headers=bearer(await member(make_actor, kings, "kings", "owner")),
    )
    response = await client.get(
        "/api/v1/orgs/guys/programmes",
        headers=bearer(await member(make_actor, guys, "guys", "owner")),
    )
    assert response.json()["items"] == []
