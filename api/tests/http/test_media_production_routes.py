"""Media production enqueue routes."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def _summary(client: AsyncClient, admin: str) -> dict:
    response = await client.post(
        "/api/v1/media",
        json={"kind": "summary", "title": "AV Summary Test", "content": {"red_flags": ["x"]}},
        headers=bearer(admin),
    )
    assert response.status_code == 201
    return response.json()


async def test_generate_podcast_wrong_kind(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("av-wrong@osceguide.com", platform_admin=True)
    blog = await client.post(
        "/api/v1/media",
        json={"kind": "blog", "title": "Blog", "content": {"body_md": "hi"}},
        headers=bearer(admin),
    )
    item_id = blog.json()["id"]
    response = await client.post(
        f"/api/v1/media/{item_id}/generate-podcast",
        headers=bearer(admin),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "media_wrong_kind"


async def test_enqueue_summary_podcast_sets_status(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("av-pod@osceguide.com", platform_admin=True)
    item = await _summary(client, admin)
    response = await client.post(
        f"/api/v1/media/{item['id']}/generate-podcast",
        headers=bearer(admin),
    )
    assert response.status_code == 202
    body = response.json()
    assert body["content"]["status"] == "generating_podcast"


async def test_enqueue_twice_conflicts(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("av-twice@osceguide.com", platform_admin=True)
    item = await _summary(client, admin)
    url = f"/api/v1/media/{item['id']}/generate-podcast"
    await client.post(url, headers=bearer(admin))
    again = await client.post(url, headers=bearer(admin))
    assert again.status_code == 409
    assert again.json()["code"] == "av_already_running"
