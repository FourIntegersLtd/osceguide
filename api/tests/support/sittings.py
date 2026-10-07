"""Helpers for scheduling sittings after the rubric-only binding change."""

from __future__ import annotations

import uuid

from httpx import AsyncClient

from tests.support.tokens import bearer


async def add_programme(
    client: AsyncClient, admin_token: str, *, org_slug: str, exam_code: str = "sca", active: bool = True
) -> uuid.UUID:
    """A programme, activated unless `active=False`: a draft is not offered (B-3)."""
    response = await client.post(
        f"/api/v1/orgs/{org_slug}/programmes",
        json={"exam_code": exam_code},
        headers=bearer(admin_token),
    )
    assert response.status_code == 201, response.text
    programme_id = uuid.UUID(response.json()["id"])
    if active:
        activated = await client.patch(
            f"/api/v1/orgs/{org_slug}/programmes/{programme_id}",
            json={"status": "active"},
            headers=bearer(admin_token),
        )
        assert activated.status_code == 200, activated.text
    return programme_id


def create_sitting_body(
    *,
    name: str,
    programme_id: uuid.UUID,
    mode: str = "exam",
    sitting_type: str = "group_training",
) -> dict[str, str]:
    return {
        "name": name,
        "programme_id": str(programme_id),
        "mode": mode,
        "sitting_type": sitting_type,
    }
