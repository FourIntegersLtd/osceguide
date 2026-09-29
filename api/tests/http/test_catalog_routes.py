"""Exams are written by a platform admin; programmes are an organisation's own."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.core.auth import Membership
from tests.support.catalog import create_exam
from tests.support.rubrics import create_rubric
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


async def published_exam(client: AsyncClient, make_actor, code: str) -> dict:  # type: ignore[no-untyped-def]
    """An exam a programme can offer. Nothing is seeded, so it has to be written."""
    admin = await make_actor(f"exam-admin-{code}@osceguide.com", platform_admin=True)
    return await create_exam(client, admin, code=code)


async def member(make_actor, org_id: uuid.UUID, slug: str, role: str) -> str:  # type: ignore[no-untyped-def]
    return await make_actor(
        f"{role}-{slug}@example.com",
        memberships=(Membership(org_id=org_id, org_slug=slug, role=role),),
        active_org_slug=slug,
    )


async def test_the_exams_table_starts_empty(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Nothing is seeded. Four rows used to be inserted by a migration and
    mirrored by a frozen tuple in the catalog domain, so a fifth exam meant
    editing both and shipping."""
    response = await client.get("/api/v1/exams", headers=bearer(await make_actor()))
    assert response.status_code == 200
    assert response.json()["items"] == []


async def test_a_platform_admin_writes_an_exam_nobody_shipped(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    exam = await create_exam(client, admin, code="mrcp-paces", name="MRCP PACES")

    assert exam["status"] == "published"
    # What a result is recorded under: the rubric version's own id, so it
    # traces back to the exact wording it was marked against.
    assert exam["framework_id"] == exam["rubric_version_id"]

    listed = await client.get("/api/v1/exams", headers=bearer(await make_actor("someone@example.com")))
    assert [e["code"] for e in listed.json()["items"]] == ["mrcp-paces"]


async def test_an_exam_carries_its_own_timings(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    await create_exam(client, admin, code="sca")

    response = await client.get("/api/v1/exams", headers=bearer(await make_actor()))
    sca = next(e for e in response.json()["items"] if e["code"] == "sca")
    assert sca["default_simulation_seconds"] == 900


async def test_a_draft_exam_is_hidden_from_everyone_but_its_author(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    await create_exam(client, admin, code="draft-exam", publish=False)

    to_admin = await client.get("/api/v1/exams", headers=bearer(admin))
    to_anyone = await client.get("/api/v1/exams", headers=bearer(await make_actor("t@example.com")))

    assert [e["code"] for e in to_admin.json()["items"]] == ["draft-exam"]
    assert to_anyone.json()["items"] == []


async def test_an_exam_cannot_be_published_without_a_rubric(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Otherwise it could be sat, and found unmarkable when the transcript arrived."""
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    created = await client.post(
        "/api/v1/platform/exams",
        json={
            "code": "no-rubric",
            "name": "No rubric",
            "default_reading_seconds": 90,
            "default_simulation_seconds": 600,
        },
        headers=bearer(admin),
    )
    response = await client.post(
        f"/api/v1/platform/exams/{created.json()['id']}/publish", headers=bearer(admin)
    )

    assert response.status_code == 409
    assert response.json()["code"] == "exam_not_publishable"


async def test_an_exam_may_only_be_marked_with_a_platform_rubric(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """An exam belongs to everyone, so it cannot bind one institution's rubric."""
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    org_id = await seed_org(client, make_actor)
    theirs = await create_rubric(client, await member(make_actor, org_id, "kings", "owner"), org_slug="kings")
    response = await client.post(
        "/api/v1/platform/exams",
        json={
            "code": "borrowed",
            "name": "Borrowed",
            "default_reading_seconds": 90,
            "default_simulation_seconds": 600,
            "rubric_version_id": theirs["version_id"],
        },
        headers=bearer(admin),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "rubric_version_not_found"


async def test_a_code_is_taken_only_once(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    await create_exam(client, admin, code="sca")
    rubric = await create_rubric(client, admin, title="Another")

    response = await client.post(
        "/api/v1/platform/exams",
        json={
            "code": "SCA",
            "name": "Same code, different case",
            "default_reading_seconds": 90,
            "default_simulation_seconds": 600,
            "rubric_version_id": rubric["version_id"],
        },
        headers=bearer(admin),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "exam_code_taken"


async def test_an_org_admin_cannot_write_an_exam(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    response = await client.post(
        "/api/v1/platform/exams",
        json={
            "code": "ours",
            "name": "Ours",
            "default_reading_seconds": 90,
            "default_simulation_seconds": 600,
        },
        headers=bearer(await member(make_actor, org_id, "kings", "owner")),
    )
    assert response.status_code == 403


async def test_a_retired_exam_cannot_be_offered(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Past attempts keep working; nothing new may name it."""
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    exam = await create_exam(client, admin, code="sca")
    org_id = await seed_org(client, make_actor)
    await client.post(f"/api/v1/platform/exams/{exam['id']}/retire", headers=bearer(admin))

    response = await client.post(
        "/api/v1/orgs/kings/programmes",
        json={"exam_code": "sca"},
        headers=bearer(await member(make_actor, org_id, "kings", "owner")),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "unknown_exam"


async def test_a_draft_exam_cannot_be_offered(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    await create_exam(client, admin, code="sca", publish=False)
    org_id = await seed_org(client, make_actor)

    response = await client.post(
        "/api/v1/orgs/kings/programmes",
        json={"exam_code": "sca"},
        headers=bearer(await member(make_actor, org_id, "kings", "owner")),
    )

    assert response.status_code == 404


async def test_an_org_admin_adds_a_programme(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    await published_exam(client, make_actor, "plab")
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
    await published_exam(client, make_actor, "plab")
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
    await published_exam(client, make_actor, "plab")
    response = await client.post(
        "/api/v1/orgs/kings/programmes",
        json={"exam_code": "plab"},
        headers=bearer(await member(make_actor, org_id, "kings", "trainee")),
    )
    assert response.status_code == 403


async def test_a_trainee_may_read_the_programmes(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    await published_exam(client, make_actor, "sca")
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
    await published_exam(client, make_actor, "sca")
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


async def test_the_console_lists_platform_exams_in_every_status(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Drafts included, a page at a time, and narrowed by status on request."""
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    await create_exam(client, admin, code="first-live")
    await create_exam(client, admin, code="second-draft", publish=False)
    await create_exam(client, admin, code="third-live")

    first_page = await client.get("/api/v1/platform/exams", params={"limit": 2}, headers=bearer(admin))
    assert first_page.status_code == 200, first_page.text
    assert len(first_page.json()["items"]) == 2
    rest = await client.get(
        "/api/v1/platform/exams",
        params={"limit": 2, "cursor": first_page.json()["next_cursor"]},
        headers=bearer(admin),
    )
    assert rest.json()["next_cursor"] is None
    # One test transaction gives every row the same `created_at`, so the id
    # decides the order; what matters is that each exam appears exactly once.
    listed = [exam["code"] for exam in first_page.json()["items"] + rest.json()["items"]]
    assert sorted(listed) == ["first-live", "second-draft", "third-live"]

    drafts = await client.get("/api/v1/platform/exams", params={"status": "draft"}, headers=bearer(admin))
    assert [exam["code"] for exam in drafts.json()["items"]] == ["second-draft"]


async def test_only_a_platform_admin_lists_platform_exams(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    refused = await client.get("/api/v1/platform/exams", headers=bearer(await make_actor("t@example.com")))
    assert refused.status_code == 403
