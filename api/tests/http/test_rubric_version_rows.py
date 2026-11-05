"""A marking scheme's versions list: when a draft was edited, which exams use it, when it was archived."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.support.catalog import create_exam
from tests.support.rubrics import create_rubric
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def test_a_version_row_says_which_exam_uses_it_and_when_it_was_last_edited(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    exam = await create_exam(client, admin, code="sca")
    rubrics = await client.get("/api/v1/platform/rubrics", headers=bearer(admin))
    rubric_id = rubrics.json()["items"][0]["id"]
    await client.post(f"/api/v1/platform/rubrics/{rubric_id}/versions", headers=bearer(admin))

    read = await client.get(f"/api/v1/platform/rubrics/{rubric_id}", headers=bearer(admin))

    by_number = {row["version"]: row for row in read.json()["versions"]}
    assert by_number[1]["used_by_exams"] == [exam["name"]]
    assert by_number[2]["used_by_exams"] == []
    assert by_number[2]["updated_at"] is not None
    assert by_number[2]["archived_at"] is None


async def test_an_archived_version_carries_the_date_it_was_archived(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    rubric = await create_rubric(client, admin)
    base = f"/api/v1/platform/rubrics/{rubric['id']}"
    await client.post(f"{base}/versions", headers=bearer(admin))
    await client.post(f"{base}/versions/2/publish", headers=bearer(admin))

    archived = await client.post(f"{base}/versions/2/archive", headers=bearer(admin))

    assert archived.status_code == 200, archived.text
    assert archived.json()["archived_at"] is not None
    assert archived.json()["status"] == "archived"
