"""Starting an assistant session, and getting into its room.

The token route is what makes the rest of the slice reachable: before it, a
session could be created and a worker could bootstrap it, but no browser could
join, so nothing the assistant does happened end to end.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.support.fakes import FakeVoiceTokens
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


@pytest.fixture
def voice_tokens(client: AsyncClient) -> FakeVoiceTokens:
    """Replace the LiveKit adapter with a recording fake, at this slice's seam."""
    from app.features.assistant.service import get_voice_tokens

    fake = FakeVoiceTokens()
    client._transport.app.dependency_overrides[get_voice_tokens] = lambda: fake  # type: ignore[attr-defined]
    return fake


async def a_session(client: AsyncClient, token: str, session_type: str = "dashboard") -> str:
    created = await client.post(
        "/api/v1/assistant/sessions", json={"session_type": session_type}, headers=bearer(token)
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


async def test_the_owner_is_let_into_their_own_session(
    client: AsyncClient, make_actor, voice_tokens: FakeVoiceTokens
) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("assistant-owner@example.com")
    session_id = await a_session(client, token)

    response = await client.post(
        f"/api/v1/assistant/sessions/{session_id}/voice-token", headers=bearer(token)
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["room"] == f"assistant_{session_id}"
    assert body["token"] and body["server_url"]


async def test_the_token_brings_the_assistant_worker_with_it(
    client: AsyncClient, make_actor, voice_tokens: FakeVoiceTokens
) -> None:  # type: ignore[no-untyped-def]
    """The three strings `livekit_assistant_worker/metadata.py` reads, and the right family."""
    token = await make_actor("assistant-dispatch@example.com")
    session_id = await a_session(client, token)

    await client.post(f"/api/v1/assistant/sessions/{session_id}/voice-token", headers=bearer(token))

    issued = voice_tokens.issued[-1]
    assert issued["agent_name"] == "assistant-self-hosted"
    metadata = issued["dispatch_metadata"]
    assert metadata["session_id"] == session_id
    assert metadata["backend"]
    assert metadata["candidate_ref"] == issued["identity"]


async def test_somebody_elses_session_is_refused(
    client: AsyncClient, make_actor, voice_tokens: FakeVoiceTokens
) -> None:  # type: ignore[no-untyped-def]
    owner = await make_actor("assistant-mine@example.com")
    stranger = await make_actor("assistant-theirs@example.com")
    session_id = await a_session(client, owner)

    response = await client.post(
        f"/api/v1/assistant/sessions/{session_id}/voice-token", headers=bearer(stranger)
    )

    assert response.status_code == 403
    assert response.json()["code"] == "assistant_session_not_yours"
    assert not voice_tokens.issued


async def test_a_finished_session_cannot_be_rejoined(
    client: AsyncClient, make_actor, voice_tokens: FakeVoiceTokens
) -> None:  # type: ignore[no-untyped-def]
    from app.core.settings import get_settings

    token = await make_actor("assistant-finished@example.com")
    session_id = await a_session(client, token)
    settings = get_settings()
    await client.post(
        f"/api/worker/sessions/{session_id}/complete",
        json={"end_reason": "user_left", "usage": {}},
        headers={settings.worker_secret_header: settings.worker_secret},
    )

    response = await client.post(
        f"/api/v1/assistant/sessions/{session_id}/voice-token", headers=bearer(token)
    )

    assert response.status_code == 409
    assert response.json()["code"] == "assistant_session_not_joinable"


async def test_a_session_that_does_not_exist_is_a_404(
    client: AsyncClient, make_actor, voice_tokens: FakeVoiceTokens
) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("assistant-missing@example.com")
    response = await client.post(
        f"/api/v1/assistant/sessions/{uuid.uuid4()}/voice-token", headers=bearer(token)
    )
    assert response.status_code == 404
    assert response.json()["code"] == "assistant_session_not_found"
