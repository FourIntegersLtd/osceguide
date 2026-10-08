"""A summary with its podcast script written, for the media-production routes."""

from __future__ import annotations

from httpx import AsyncClient

from tests.support.tokens import bearer

SCRIPT = "Ben: Chest pain on exertion needs an ECG.\n\nMichelle: And a same-day review."
LINES = ["Ben: Chest pain on exertion needs an ECG.", "Michelle: And a same-day review."]


async def a_summary(client: AsyncClient, admin: str, *, checked: bool = True) -> dict:
    """A summary with its podcast script written; `checked` says whether that script has been read."""
    content: dict = {"red_flags": ["x"], "script": SCRIPT}
    if checked:
        content["review"] = {"script": {"lines": LINES}}
    response = await client.post(
        "/api/v1/media",
        json={"kind": "summary", "title": "AV Summary Test", "content": content},
        headers=bearer(admin),
    )
    assert response.status_code == 201
    return response.json()
