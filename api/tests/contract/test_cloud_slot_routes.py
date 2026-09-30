"""The cloud-slot half of the worker contract.

`voice_infra/cloud_slot.py` posts `{"room_name": ...}` to
`/api/worker/livekit-cloud-slot/extend` when a session starts and to
`.../release` on shutdown, with the shared secret header. It never reads the
response, so the shape matters less than the fact that these exist and are
guarded — a backend that does not serve them leaks a Cloud slot per session
until the expiry reclaims it, and the cap silently shrinks over a busy day.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.settings import get_settings

pytestmark = pytest.mark.db


def worker_headers() -> dict[str, str]:
    settings = get_settings()
    return {settings.worker_secret_header: settings.worker_secret}


@pytest.mark.parametrize("action", ["extend", "release"])
async def test_a_cloud_slot_route_needs_the_worker_secret(client: AsyncClient, action: str) -> None:
    response = await client.post(f"/api/worker/livekit-cloud-slot/{action}", json={"room_name": "attempt_1"})

    assert response.status_code == 401


@pytest.mark.parametrize("action", ["extend", "release"])
async def test_a_cloud_slot_route_answers_without_redis(client: AsyncClient, action: str) -> None:
    """Redis is off in tests, and that must not fail the call.

    The worker treats these as best effort and carries on regardless; failing
    the request would end a live session over an accounting detail.
    """
    response = await client.post(
        f"/api/worker/livekit-cloud-slot/{action}",
        json={"room_name": "attempt_1"},
        headers=worker_headers(),
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"room_name": "attempt_1", "changed": False}


async def test_the_paths_are_the_ones_the_worker_is_configured_with(client: AsyncClient) -> None:
    """These spellings live in `voice_infra/config.py` defaults, so they are
    the contract rather than a choice this codebase gets to make."""
    from app.main import create_app

    paths = {r.path for r in create_app().routes if hasattr(r, "path")}

    assert "/api/worker/livekit-cloud-slot/extend" in paths
    assert "/api/worker/livekit-cloud-slot/release" in paths
