"""Archiving a rubric version: refused while an exam is marked against it, and never strands the rubric."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.support.catalog import create_exam
from tests.support.rubrics import create_rubric
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def test_a_version_an_exam_is_marked_against_cannot_be_archived(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    await create_exam(client, admin, code="sca")
    rubrics = await client.get("/api/v1/platform/rubrics", headers=bearer(admin))
    rubric_id = rubrics.json()["items"][0]["id"]

    refused = await client.post(
        f"/api/v1/platform/rubrics/{rubric_id}/versions/1/archive", headers=bearer(admin)
    )

    assert refused.status_code == 409, refused.text
    assert refused.json()["code"] == "not_archivable"
    assert refused.json()["details"] == {"reason": "in_use", "exams": 1, "sittings": 0}


async def test_archiving_the_current_version_falls_back_to_the_previous_published_one(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    rubric = await create_rubric(client, admin)
    base = f"/api/v1/platform/rubrics/{rubric['id']}"
    first_id = rubric["version_id"]
    await client.post(f"{base}/versions", headers=bearer(admin))
    published = await client.post(f"{base}/versions/2/publish", headers=bearer(admin))
    assert published.status_code == 200, published.text
    current = await client.get(base, headers=bearer(admin))
    assert current.json()["current_version_id"] == published.json()["id"]

    archived = await client.post(f"{base}/versions/2/archive", headers=bearer(admin))

    assert archived.status_code == 200, archived.text
    after = await client.get(base, headers=bearer(admin))
    assert after.json()["current_version_id"] == first_id
