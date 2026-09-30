"""Authoring a rubric through the API, as the platform and as an institution.

The same tables and the same lifecycle behind two doors. What these pin is the
boundary between them: an org may read the platform's rubrics and may not touch
them, and the platform may not reach into an org's.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.core.auth import Membership
from tests.support.catalog import create_exam
from tests.support.rubrics import FULL_RUBRIC, MINIMAL_RUBRIC, PACING, SYSTEM_PROMPT, create_rubric
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


async def test_a_platform_admin_authors_and_publishes_a_rubric(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("admin@osceguide.com", platform_admin=True)

    rubric = await create_rubric(client, admin, structure=FULL_RUBRIC, title="SCA marking")

    assert rubric["owner_kind"] == "platform"
    assert rubric["org_id"] is None
    read = await client.get(f"/api/v1/platform/rubrics/{rubric['id']}", headers=bearer(admin))
    version = read.json()["versions"][0]
    assert version["status"] == "published"
    # Derived on the way out, so an author sees what their domains came to.
    assert version["result_schema"]["required"][:2] == ["global_skills", "tasks"]


async def test_the_rubric_table_starts_empty(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Nothing is seeded. A rubric exists because somebody wrote it."""
    admin = await make_actor("admin@osceguide.com", platform_admin=True)

    response = await client.get("/api/v1/platform/rubrics", headers=bearer(admin))

    assert response.status_code == 200
    assert response.json()["items"] == []


async def test_an_ordinary_user_cannot_author_a_platform_rubric(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    someone = await make_actor("trainee@example.com")

    response = await client.post(
        "/api/v1/platform/rubrics",
        json={"title": "Mine", "structure": MINIMAL_RUBRIC, "system_prompt": SYSTEM_PROMPT, "pacing": PACING},
        headers=bearer(someone),
    )

    assert response.status_code == 403


async def test_a_rubric_that_could_not_be_marked_against_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Saved as a draft that lists what is wrong; publishing it is what is refused."""
    admin = await make_actor("admin@osceguide.com", platform_admin=True)

    response = await client.post(
        "/api/v1/platform/rubrics",
        json={
            "title": "Broken",
            "structure": {"scale": [], "domains": []},
            "system_prompt": SYSTEM_PROMPT,
            "pacing": PACING,
        },
        headers=bearer(admin),
    )

    assert response.status_code == 201, response.text
    draft = response.json()["versions"][0]
    assert draft["problems"] == [
        {"path": "", "message": "A rubric needs a scale: the scores a competency may be given."}
    ]
    assert draft["result_schema"] == {}
    published = await client.post(
        f"/api/v1/platform/rubrics/{response.json()['id']}/versions/1/publish", headers=bearer(admin)
    )
    assert published.status_code == 422
    assert published.json()["code"] == "invalid_rubric"


async def test_a_published_version_cannot_be_edited(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """It is what past attempts were marked against."""
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    rubric = await create_rubric(client, admin)

    response = await client.patch(
        f"/api/v1/platform/rubrics/{rubric['id']}/versions/1",
        json={"structure": MINIMAL_RUBRIC, "system_prompt": "Different.", "pacing": PACING},
        headers=bearer(admin),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "not_editable"


async def test_a_new_version_is_seeded_from_the_published_one(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    rubric = await create_rubric(client, admin, structure=FULL_RUBRIC)

    response = await client.post(f"/api/v1/platform/rubrics/{rubric['id']}/versions", headers=bearer(admin))

    assert response.status_code == 201
    draft = response.json()
    assert draft["version"] == 2 and draft["status"] == "draft"
    assert draft["structure"] == FULL_RUBRIC


async def test_a_half_written_draft_cannot_be_published(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """A draft may be incomplete; a published version may not, because attempts use it."""
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    rubric = await create_rubric(client, admin, publish=False)
    await client.patch(
        f"/api/v1/platform/rubrics/{rubric['id']}/versions/1",
        json={"structure": MINIMAL_RUBRIC, "system_prompt": "   ", "pacing": PACING},
        headers=bearer(admin),
    )

    response = await client.post(
        f"/api/v1/platform/rubrics/{rubric['id']}/versions/1/publish", headers=bearer(admin)
    )

    assert response.status_code == 422
    assert "marking instructions" in response.json()["message"]


# --- the two doors ----------------------------------------------------------


async def test_an_org_authors_its_own_rubric(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    org_admin = await member(make_actor, org_id, "kings", "admin")

    rubric = await create_rubric(client, org_admin, org_slug="kings", title="Ours")

    assert rubric["owner_kind"] == "org"
    assert rubric["org_id"] == str(org_id)


async def test_platform_rubrics_can_be_searched_by_title(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("search-admin@osceguide.com", platform_admin=True)
    await create_rubric(client, admin, title="SCA marking")
    await create_rubric(client, admin, title="PLAB marking")

    response = await client.get("/api/v1/platform/rubrics", params={"search": "sca"}, headers=bearer(admin))

    assert response.status_code == 200, response.text
    assert [item["title"] for item in response.json()["items"]] == ["SCA marking"]


async def test_platform_rubrics_can_be_narrowed_to_the_one_an_exam_uses(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """The server-side twin of platform-web's `rubricMatchesExam`: a rubric
    matches when one of its versions is the exam's current `rubric_version_id`."""
    admin = await make_actor("exam-match-admin@osceguide.com", platform_admin=True)
    bound = await create_exam(client, admin, code="sca")
    await create_rubric(client, admin, title="Unrelated rubric")

    response = await client.get(
        "/api/v1/platform/rubrics", params={"exam_code": "sca"}, headers=bearer(admin)
    )

    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()["items"]] == [bound["rubric_id"]]


async def test_an_org_sees_the_platform_library_alongside_its_own(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    platform_rubric = await create_rubric(client, admin, title="Platform rubric")
    org_id = await seed_org(client, make_actor)
    org_admin = await member(make_actor, org_id, "kings", "admin")
    own = await create_rubric(client, org_admin, org_slug="kings", title="Ours")

    response = await client.get("/api/v1/orgs/kings/rubrics", headers=bearer(org_admin))

    titles = {item["title"] for item in response.json()["items"]}
    assert titles == {"Platform rubric", "Ours"}
    assert {platform_rubric["id"], own["id"]} == {item["id"] for item in response.json()["items"]}


async def test_an_org_admin_cannot_edit_a_platform_rubric(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """It may read the library and mark with it; it may not rewrite it."""
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    platform_rubric = await create_rubric(client, admin, publish=False)
    org_id = await seed_org(client, make_actor)
    org_admin = await member(make_actor, org_id, "kings", "admin")

    response = await client.patch(
        f"/api/v1/orgs/kings/rubrics/{platform_rubric['id']}/versions/1",
        json={"structure": MINIMAL_RUBRIC, "system_prompt": "Mine now.", "pacing": PACING},
        headers=bearer(org_admin),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "rubric_not_found"


async def test_a_platform_admin_is_not_thereby_an_org_admin(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Deliberate: `OrgAdmin` sets allow_platform_admin=False."""
    org_id = await seed_org(client, make_actor)
    org_admin = await member(make_actor, org_id, "kings", "admin")
    org_rubric = await create_rubric(client, org_admin, org_slug="kings", publish=False)
    admin = await make_actor("admin@osceguide.com", platform_admin=True)

    response = await client.patch(
        f"/api/v1/orgs/kings/rubrics/{org_rubric['id']}/versions/1",
        json={"structure": MINIMAL_RUBRIC, "system_prompt": "Theirs now.", "pacing": PACING},
        headers=bearer(admin),
    )

    assert response.status_code == 403


async def test_another_orgs_rubric_is_invisible(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    kings = await seed_org(client, make_actor, "kings")
    kings_admin = await member(make_actor, kings, "kings", "admin")
    theirs = await create_rubric(client, kings_admin, org_slug="kings", title="Kings only")
    guys = await seed_org(client, make_actor, "guys")
    guys_admin = await member(make_actor, guys, "guys", "admin")

    listed = await client.get("/api/v1/orgs/guys/rubrics", headers=bearer(guys_admin))
    read = await client.get(f"/api/v1/orgs/guys/rubrics/{theirs['id']}", headers=bearer(guys_admin))

    assert listed.json()["items"] == []
    assert read.status_code == 404


async def test_a_trainee_may_not_author_a_rubric(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    trainee = await member(make_actor, org_id, "kings", "trainee")

    response = await client.post(
        "/api/v1/orgs/kings/rubrics",
        json={"title": "Mine", "structure": MINIMAL_RUBRIC, "system_prompt": SYSTEM_PROMPT, "pacing": PACING},
        headers=bearer(trainee),
    )

    assert response.status_code == 403


# --- renaming (R-7) ----------------------------------------------------------


async def test_a_platform_admin_renames_a_platform_rubric(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    rubric = await create_rubric(client, admin, title="Old title")

    response = await client.patch(
        f"/api/v1/platform/rubrics/{rubric['id']}", json={"title": "New title"}, headers=bearer(admin)
    )

    assert response.status_code == 200, response.text
    assert response.json()["title"] == "New title"
    reread = await client.get(f"/api/v1/platform/rubrics/{rubric['id']}", headers=bearer(admin))
    assert reread.json()["title"] == "New title"


async def test_an_org_admin_renames_its_own_rubric(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    org_admin = await member(make_actor, org_id, "kings", "admin")
    rubric = await create_rubric(client, org_admin, org_slug="kings", title="Ours")

    response = await client.patch(
        f"/api/v1/orgs/kings/rubrics/{rubric['id']}",
        json={"title": "Ours, renamed"},
        headers=bearer(org_admin),
    )

    assert response.status_code == 200, response.text
    assert response.json()["title"] == "Ours, renamed"


async def test_an_org_admin_cannot_rename_a_platform_rubric(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    platform_rubric = await create_rubric(client, admin, title="Platform rubric")
    org_id = await seed_org(client, make_actor)
    org_admin = await member(make_actor, org_id, "kings", "admin")

    response = await client.patch(
        f"/api/v1/orgs/kings/rubrics/{platform_rubric['id']}",
        json={"title": "Stolen"},
        headers=bearer(org_admin),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "rubric_not_found"


async def test_a_blank_title_is_refused_with_422(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    rubric = await create_rubric(client, admin, title="Keeps its title")

    response = await client.patch(
        f"/api/v1/platform/rubrics/{rubric['id']}", json={"title": "   "}, headers=bearer(admin)
    )

    assert response.status_code == 422, response.text
