"""Platform content generation routes (mocked OpenAI)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def test_generate_blog_for_an_exam_with_no_settings_uses_the_neutral_prompt(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("gen-admin@osceguide.com", platform_admin=True)
    captured: dict[str, str] = {}

    async def fake_json_completion(*, settings, system: str, user: str) -> dict:  # type: ignore[no-untyped-def]
        captured["system"] = system
        captured["user"] = user
        return {"title": "T", "content": "Body", "url": "t"}

    with patch(
        "app.features.generation.service._json_completion",
        new=AsyncMock(side_effect=fake_json_completion),
    ):
        res = await client.post(
            "/api/v1/platform/generate/blog",
            headers=bearer(admin),
            json={"prompt": "Write about asthma control", "exam_code": "sca"},
        )

    assert res.status_code == 200, res.text
    # No `sca` exam row in this database, so its settings are the defaults: the
    # exam-neutral blog prompt, not SCA's. The seeded SCA exam names `sca.blog`.
    from app.features.generation.exam_prompts import GENERIC_BLOG_PROMPT

    assert captured["system"].startswith(GENERIC_BLOG_PROMPT)
    assert res.json()["content"]["body_md"] == "Body"


async def test_generate_podcast_route(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("gen-pod@osceguide.com", platform_admin=True)

    with patch(
        "app.features.generation.service._json_completion",
        new=AsyncMock(return_value={"script": 'Ben: "hello"\nTom: "hi"'}),
    ):
        res = await client.post(
            "/api/v1/platform/generate/podcast",
            headers=bearer(admin),
            json={"prompt": "Topic: hypertension", "exam_code": "sca"},
        )

    assert res.status_code == 200, res.text
    assert "hello" in res.json()["content"]["script"]
