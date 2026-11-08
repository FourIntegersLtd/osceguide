"""The rubric builder's routes (plan §8, Stage 4): preview, copy, starting points, draft instructions.

Each is behind the same doors as authoring a rubric: an org admin for the
org's own, a platform admin for the platform's, and neither for the other's.
"""

from __future__ import annotations

import copy
import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.rubrics import domain
from app.features.rubrics.authoring import blank_scheme, blank_structure
from app.features.rubrics.models import RubricVersion
from app.features.rubrics.validation import IDENTIFIER_MESSAGE
from tests.http.test_rubrics_routes import member, seed_org
from tests.support.rubrics import FULL_RUBRIC, PACING, SYSTEM_PROMPT, create_rubric
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

ORG_RUBRICS = "/api/v1/orgs/kings/rubrics"


def instructed_structure() -> dict[str, Any]:
    """A blank rubric whose domain and competency carry the author's own wording."""
    structure = blank_structure()
    structure["sections"][0]["instructions"] = "Consulting well."
    structure["sections"][0]["competencies"][0]["instructions"] = "Opens with an open question."
    return structure


async def test_a_draft_is_saved_while_invalid_and_says_what_is_left(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    admin = await member(make_actor, org_id, "kings", "admin")
    unfinished = {"schemaVersion": 2, "rating": {"kind": "rag"}, "sections": []}

    created = await client.post(
        ORG_RUBRICS,
        json={
            "title": "Half done",
            "structure": unfinished,
            "system_prompt": SYSTEM_PROMPT,
            "pacing": PACING,
        },
        headers=bearer(admin),
    )

    assert created.status_code == 201, created.text
    draft = created.json()["versions"][0]
    assert draft["problems"] == [
        {
            "path": "sections",
            "message": "Add at least one Domain or section, otherwise the marker has nothing to mark.",
        }
    ]
    assert draft["result_schema"] == {}
    # Publishing is what refuses it, with the same problems listed.
    published = await client.post(
        f"{ORG_RUBRICS}/{created.json()['id']}/versions/1/publish", headers=bearer(admin)
    )
    assert published.status_code == 422
    assert published.json()["details"]["errors"] == draft["problems"]


async def test_a_preview_shows_what_a_valid_draft_comes_to(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    admin = await member(make_actor, org_id, "kings", "admin")

    response = await client.post(
        f"{ORG_RUBRICS}/preview", json={"structure": blank_structure()}, headers=bearer(admin)
    )

    assert response.status_code == 200, response.text
    preview = response.json()
    assert preview["valid"] is True
    assert preview["problems"] == []
    assert preview["rating"] == {
        "kind": "rag",
        "field": "score",
        "scale": ["G", "A", "R"],
        "minimum": None,
        "maximum": None,
        "step": "number",
        "points": None,
    }
    assert preview["sample_result"] == {
        "domain_1": {
            "competency_1": {
                "score": "G",
                "evidence": "Sample evidence for Competency 1.",
                "explanation": "Sample explanation for Competency 1.",
            }
        }
    }
    assert preview["sample_totals"]["domains"][0]["counts"] == {"G": 1, "A": 0, "R": 0}
    assert list(preview["result_schema"]["properties"]) == ["domain_1"]
    assert preview["display"]["domain"]["aggregate"] == "ragCounts"


async def test_a_preview_of_an_invalid_draft_is_its_problems(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    structure = blank_structure()
    structure["sections"][0]["competencyFields"][0]["id"] = "Bad Id"

    response = await client.post(
        "/api/v1/platform/rubrics/preview", json={"structure": structure}, headers=bearer(admin)
    )

    assert response.status_code == 200, response.text
    preview = response.json()
    assert preview["valid"] is False
    assert [problem["path"] for problem in preview["problems"]] == [
        "sections[0].competencyFields[0].id",
        "sections[0].competencyFields[0].id",
    ]
    assert preview["sample_result"] is None


async def test_an_org_copies_a_published_platform_rubric_into_its_own_draft(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    platform_admin = await make_actor("admin@osceguide.com", platform_admin=True)
    source = await create_rubric(client, platform_admin, structure=FULL_RUBRIC, title="SCA marking")
    org_id = await seed_org(client, make_actor)
    admin = await member(make_actor, org_id, "kings", "admin")

    response = await client.post(
        f"{ORG_RUBRICS}/copy", json={"source_rubric_id": source["id"]}, headers=bearer(admin)
    )

    assert response.status_code == 201, response.text
    copied = response.json()
    assert (copied["owner_kind"], copied["org_id"], copied["title"]) == (
        "org",
        str(org_id),
        "SCA marking (copy)",
    )
    draft = copied["versions"][0]
    assert (draft["version"], draft["status"], draft["problems"]) == (1, "draft", [])
    assert draft["structure"]["schemaVersion"] == 3
    assert draft["structure"]["basedOn"] == {"rubricId": source["id"], "version": 1, "title": "SCA marking"}
    assert (draft["system_prompt"], draft["pacing"]) == (SYSTEM_PROMPT, PACING)
    assert draft["result_schema"]["required"][:2] == ["global_skills", "tasks"]
    # The copy is the org's own to publish; the platform's is untouched.
    published = await client.post(f"{ORG_RUBRICS}/{copied['id']}/versions/1/publish", headers=bearer(admin))
    assert published.status_code == 200, published.text


async def test_a_blank_start_is_a_publishable_skeleton(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    admin = await member(make_actor, org_id, "kings", "admin")

    response = await client.post(f"{ORG_RUBRICS}/copy", json={}, headers=bearer(admin))

    assert response.status_code == 201, response.text
    draft = response.json()["versions"][0]
    assert response.json()["title"] == "Untitled rubric"
    assert draft["structure"] == blank_scheme()
    assert draft["problems"] == []
    published = await client.post(
        f"{ORG_RUBRICS}/{response.json()['id']}/versions/1/publish", headers=bearer(admin)
    )
    assert published.status_code == 200, published.text


async def test_another_orgs_rubric_cannot_be_copied(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    other_id = await seed_org(client, make_actor, slug="guys")
    other_admin = await member(make_actor, other_id, "guys", "admin")
    theirs = await create_rubric(client, other_admin, org_slug="guys", title="Guy's own")
    org_id = await seed_org(client, make_actor)
    admin = await member(make_actor, org_id, "kings", "admin")

    response = await client.post(
        f"{ORG_RUBRICS}/copy", json={"source_rubric_id": theirs["id"]}, headers=bearer(admin)
    )

    assert response.status_code == 404
    assert response.json()["code"] == "rubric_not_found"


async def test_an_unpublished_rubric_cannot_be_copied(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    platform_admin = await make_actor("admin@osceguide.com", platform_admin=True)
    draft_only = await create_rubric(client, platform_admin, title="Still drafting", publish=False)

    response = await client.post(
        "/api/v1/platform/rubrics/copy",
        json={"source_rubric_id": draft_only["id"]},
        headers=bearer(platform_admin),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "rubric_version_not_published"


async def test_starting_points_are_blank_then_the_platform_then_the_orgs_own(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    platform_admin = await make_actor("admin@osceguide.com", platform_admin=True)
    await create_rubric(client, platform_admin, structure=FULL_RUBRIC, title="SCA marking")
    await create_rubric(client, platform_admin, title="Platform draft", publish=False)
    other_id = await seed_org(client, make_actor, slug="guys")
    other_admin = await member(make_actor, other_id, "guys", "admin")
    await create_rubric(client, other_admin, org_slug="guys", title="Guy's own")
    org_id = await seed_org(client, make_actor)
    admin = await member(make_actor, org_id, "kings", "admin")
    await create_rubric(client, admin, org_slug="kings", title="Kings OSCE")

    response = await client.get(f"{ORG_RUBRICS}/starting-points", headers=bearer(admin))

    assert response.status_code == 200, response.text
    assert [
        (
            item["kind"],
            item["title"],
            item["version"],
            item["rating_kind"],
            item["domains"],
            item["competency_count"],
        )
        for item in response.json()["items"]
    ] == [
        ("blank", "Blank rubric", None, "rag", ["Domain 1"], 1),
        ("platform", "SCA marking", 1, "rag", ["Global skills", "Tasks"], 3),
        ("own", "Kings OSCE", 1, "rag", ["Consulting"], 1),
    ]


async def test_draft_instructions_come_from_the_copied_rubric_then_the_role(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    platform_admin = await make_actor("admin@osceguide.com", platform_admin=True)
    source = await create_rubric(client, platform_admin, structure=instructed_structure(), title="Consulting")
    org_id = await seed_org(client, make_actor)
    admin = await member(make_actor, org_id, "kings", "admin")
    copied = await client.post(
        f"{ORG_RUBRICS}/copy", json={"source_rubric_id": source["id"]}, headers=bearer(admin)
    )
    structure = copy.deepcopy(copied.json()["versions"][0]["structure"])
    # The author adds a competency of their own: the source has no wording for it.
    structure["outline"][0]["competencies"].append(
        {"id": "competency_2", "label": "Closes", "instructions": ""}
    )

    response = await client.post(
        f"{ORG_RUBRICS}/draft-instructions", json={"structure": structure}, headers=bearer(admin)
    )

    assert response.status_code == 200, response.text
    assert [
        (item["path"], item["key"], item["source"], item["has_instructions"])
        for item in response.json()["items"]
    ] == [
        ("sections[0]", "domain_1", "rubric", True),
        ("sections[0].competencies[0]", "domain_1.competency_1", "rubric", True),
        ("sections[0].competencies[1]", "domain_1.competency_2", "generic", False),
        ("sections[0].competencyFields[0]", "domain_1.*.score", "generic", False),
        ("sections[0].competencyFields[1]", "domain_1.*.evidence", "generic", False),
        ("sections[0].competencyFields[2]", "domain_1.*.explanation", "generic", False),
    ]
    texts = [item["text"] for item in response.json()["items"]]
    assert texts[:3] == [
        "Consulting well.",
        "Opens with an open question.",
        "What the candidate must do to meet this competency, and what falls short.",
    ]


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("post", "/preview", {"structure": {}}),
        ("post", "/copy", {}),
        ("get", "/starting-points", None),
        ("post", "/draft-instructions", {"structure": {}}),
    ],
    ids=["preview", "copy", "starting-points", "draft-instructions"],
)
async def test_only_an_org_admin_uses_the_builder(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, method: str, path: str, body: dict[str, Any] | None
) -> None:
    """A trainee may not author, and a platform admin is deliberately not an org admin."""
    org_id = await seed_org(client, make_actor)
    trainee = await member(make_actor, org_id, "kings", "trainee")
    platform_admin = await make_actor("root@osceguide.com", platform_admin=True)

    for token in (trainee, platform_admin):
        response = await client.request(
            method.upper(), f"{ORG_RUBRICS}{path}", json=body, headers=bearer(token)
        )
        assert response.status_code == 403, (token, response.text)


async def test_a_structure_that_is_neither_version_is_refused_draft_instructions(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("admin@osceguide.com", platform_admin=True)

    response = await client.post(
        "/api/v1/platform/rubrics/draft-instructions", json={"structure": {}}, headers=bearer(admin)
    )

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_rubric"


# --- The author's scheme (schemaVersion 3) -------------------------------------


async def _stored_structure(db_session: AsyncSession, version_id: str) -> dict[str, Any]:
    row = await db_session.execute(
        select(RubricVersion.structure).where(RubricVersion.id == uuid.UUID(version_id))
    )
    return dict(row.scalar_one())


async def test_an_invalid_scheme_draft_saves_but_publish_refuses_at_its_block(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    admin = await member(make_actor, org_id, "kings", "admin")
    created = await client.post(f"{ORG_RUBRICS}/copy", json={}, headers=bearer(admin))
    rubric_id, version = created.json()["id"], created.json()["versions"][0]
    structure = copy.deepcopy(version["structure"])
    structure["outline"][0]["competencies"][0]["id"] = "Bad Id"

    saved = await client.patch(
        f"{ORG_RUBRICS}/{rubric_id}/versions/1",
        json={
            "structure": structure,
            "system_prompt": version["system_prompt"],
            "pacing": version["pacing"],
            "revision": version["revision"],
        },
        headers=bearer(admin),
    )

    assert saved.status_code == 200, saved.text
    problems = [{"path": "outline[0].competencies[0].id", "message": IDENTIFIER_MESSAGE}]
    assert saved.json()["problems"] == problems
    published = await client.post(f"{ORG_RUBRICS}/{rubric_id}/versions/1/publish", headers=bearer(admin))
    assert published.status_code == 422
    assert published.json()["code"] == "invalid_rubric"
    assert published.json()["details"]["errors"] == problems


async def test_a_published_v2_version_reads_as_a_scheme_and_the_row_is_unchanged(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    platform_admin = await make_actor("admin@osceguide.com", platform_admin=True)
    rubric = await create_rubric(client, platform_admin, structure=FULL_RUBRIC)

    read = await client.get(f"/api/v1/platform/rubrics/{rubric['id']}", headers=bearer(platform_admin))

    assert read.status_code == 200, read.text
    assert read.json()["versions"][0]["structure"]["schemaVersion"] == 3
    assert await _stored_structure(db_session, rubric["version_id"]) == FULL_RUBRIC


async def test_a_new_draft_from_a_v2_version_is_stored_as_a_scheme(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    platform_admin = await make_actor("admin@osceguide.com", platform_admin=True)
    rubric = await create_rubric(client, platform_admin, structure=FULL_RUBRIC)

    response = await client.post(
        f"/api/v1/platform/rubrics/{rubric['id']}/versions", headers=bearer(platform_admin)
    )

    assert response.status_code == 201, response.text
    stored = await _stored_structure(db_session, response.json()["id"])
    assert stored["schemaVersion"] == 3
    assert domain.upgrade_structure(stored) == domain.upgrade_structure(FULL_RUBRIC)


async def test_a_copied_platform_rubric_is_stored_as_a_scheme(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    platform_admin = await make_actor("admin@osceguide.com", platform_admin=True)
    source = await create_rubric(client, platform_admin, structure=FULL_RUBRIC, title="SCA marking")
    org_id = await seed_org(client, make_actor)
    admin = await member(make_actor, org_id, "kings", "admin")

    response = await client.post(
        f"{ORG_RUBRICS}/copy", json={"source_rubric_id": source["id"]}, headers=bearer(admin)
    )

    assert response.status_code == 201, response.text
    stored = await _stored_structure(db_session, response.json()["versions"][0]["id"])
    assert stored["schemaVersion"] == 3
    assert stored["basedOn"] == {"rubricId": source["id"], "version": 1, "title": "SCA marking"}
