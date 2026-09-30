"""Station autogenerate draft over HTTP (mocked OpenAI)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from httpx import AsyncClient

from app.core.auth import Membership
from app.features.stations.station_ai import (
    StationContentAutogenerateModel,
    StationContentBlockModel,
)
from tests.support.catalog import create_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

TEMPLATE_STRUCTURE = {
    "schemaVersion": 1,
    "generation": {"profileKey": "sca.station"},
    "sections": [
        {
            "id": "main",
            "title": "Main",
            "blocks": [
                {
                    "id": "notes",
                    "type": "longText",
                    "label": "Notes",
                    "required": True,
                },
                {
                    "id": "explanation",
                    "type": "longText",
                    "label": "Explanation",
                    "required": False,
                },
            ],
        },
    ],
}


async def org_with_admin(client: AsyncClient, make_actor, slug: str = "kings"):  # type: ignore[no-untyped-def]
    root = await make_actor(f"root-{slug}@osceguide.com", platform_admin=True)
    created = await client.post(
        "/api/v1/platform/organizations",
        json={"slug": slug, "name": slug.title(), "org_type": "institution"},
        headers=bearer(root),
    )
    org_id = UUID(created.json()["id"])
    admin = await make_actor(
        f"admin-{slug}@example.com",
        memberships=(Membership(org_id=org_id, org_slug=slug, role="owner"),),
        active_org_slug=slug,
    )
    await create_exam(client, root, code="sca")
    return org_id, admin


async def published_template_version(client: AsyncClient, admin: str, slug: str = "kings") -> UUID:
    created = await client.post(
        f"/api/v1/orgs/{slug}/station-templates",
        json={"title": "SCA consultation", "exam_code": "sca", "structure": TEMPLATE_STRUCTURE},
        headers=bearer(admin),
    )
    assert created.status_code == 201, created.text
    template_id = created.json()["id"]
    published = await client.post(
        f"/api/v1/orgs/{slug}/station-templates/{template_id}/publish",
        headers=bearer(admin),
    )
    assert published.status_code == 200, published.text
    return UUID(published.json()["id"])


async def test_autogenerate_station_draft_success(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    version_id = await published_template_version(client, admin)
    mock_parsed = StationContentAutogenerateModel(
        title="Chest pain case",
        blocks=[
            StationContentBlockModel(
                blockId="notes",
                value="A 55-year-old presents with central chest pain.",
            ),
        ],
    )

    with patch(
        "app.features.stations.station_autogenerate.generate_station_autogenerate",
        new=AsyncMock(return_value=(mock_parsed, "")),
    ):
        res = await client.post(
            "/api/v1/orgs/kings/stations/autogenerate-draft",
            headers=bearer(admin),
            json={
                "prompt": "Chest pain in a 55-year-old smoker",
                "template_version_id": str(version_id),
            },
        )

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["suggested_title"] == "Chest pain case"
    assert body["content"]["notes"] == "A 55-year-old presents with central chest pain."


async def test_autogenerate_station_draft_includes_sca_station_prompt(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    version_id = await published_template_version(client, admin)
    captured_messages: list[dict[str, str]] = []

    async def capture(messages, *, settings, **kwargs):  # type: ignore[no-untyped-def]
        captured_messages.extend(messages)
        return (
            StationContentAutogenerateModel(
                title="Case",
                blocks=[StationContentBlockModel(blockId="notes", value="Filled notes.")],
            ),
            "",
        )

    with patch(
        "app.features.stations.station_autogenerate.generate_station_autogenerate",
        new=AsyncMock(side_effect=capture),
    ):
        res = await client.post(
            "/api/v1/orgs/kings/stations/autogenerate-draft",
            headers=bearer(admin),
            json={"prompt": "Abdominal pain in a young woman", "template_version_id": str(version_id)},
        )

    assert res.status_code == 200, res.text
    system = captured_messages[0]["content"]
    user_payload = json.loads(captured_messages[1]["content"])
    assert "UK primary care" in system
    assert "recent_notes" in system
    explanation_hint = user_payload.get("blockGenerationHints", {}).get("explanation", "")
    assert "MUACLW" in explanation_hint


async def test_autogenerate_station_draft_requires_prompt(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    version_id = await published_template_version(client, admin)
    res = await client.post(
        "/api/v1/orgs/kings/stations/autogenerate-draft",
        headers=bearer(admin),
        json={"prompt": "", "template_version_id": str(version_id)},
    )
    assert res.status_code == 422
