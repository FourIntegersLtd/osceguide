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


async def test_a_help_session_speaks_from_the_faq_rather_than_a_placeholder(
    client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    """The whole of A-2: this used to be one sentence of placeholder text."""
    from app.features.assistant import repository
    from app.features.assistant.content.prompts.faq_block import FAQ_BLOCK_HEADER

    token = await make_actor("assistant-help@example.com")
    session_id = await a_session(client, token, "help")

    row = await repository.by_id(db_session, uuid.UUID(session_id))
    assert row is not None
    assert FAQ_BLOCK_HEADER in row.instructions


async def test_a_help_session_is_answered_for_the_screen_the_user_is_on(
    client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    """The client's own navigation decides the labels and which entries exist."""
    from app.features.assistant import repository

    token = await make_actor("assistant-help-nav@example.com")
    created = await client.post(
        "/api/v1/assistant/sessions",
        json={
            "session_type": "help",
            "extras": {
                "client": {
                    "surface": "exam",
                    "route": "/app/me/practice",
                    "navigation": [{"key": "messages", "label": "Talk to us", "path": "/messages"}],
                }
            },
        },
        headers=bearer(token),
    )
    assert created.status_code == 201, created.text

    row = await repository.by_id(db_session, uuid.UUID(created.json()["id"]))
    assert row is not None
    assert "Talk to us" in row.instructions
    assert "/app/me/practice" in row.instructions


async def test_a_dashboard_session_opened_on_a_topic_starts_there(
    client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    """The topic reaches the tutor's instructions as a quoted subject; a malformed one is dropped."""
    from app.features.assistant import repository

    token = await make_actor("assistant-topic@example.com")

    async def instructions_for(topic: object) -> str:
        created = await client.post(
            "/api/v1/assistant/sessions",
            json={"session_type": "dashboard", "extras": {"topic": topic}},
            headers=bearer(token),
        )
        assert created.status_code == 201, created.text
        row = await repository.by_id(db_session, uuid.UUID(created.json()["id"]))
        assert row is not None
        return row.instructions

    on_topic = await instructions_for(
        {"title": "Red flags for chest pain", "kind": "summary", "slug": "chest-pain"}
    )
    assert 'They opened this conversation to talk about "Red flags for chest pain"' in on_topic

    too_long = await instructions_for({"title": "x" * 900})
    assert "x" * 200 in too_long
    assert "x" * 201 not in too_long

    malformed = await instructions_for({"title": "Asthma", "kind": "hologram"})
    assert "They opened this conversation to talk about" not in malformed


async def test_an_onboarding_session_carries_the_scenes_it_will_demonstrate(
    client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    """Frozen with the session, so the demo matches the script that promised it."""
    from app.features.assistant import repository
    from app.features.assistant.service_content import SCENES_KEY

    token = await make_actor("assistant-onboarding@example.com")
    session_id = await a_session(client, token, "onboarding")

    row = await repository.by_id(db_session, uuid.UUID(session_id))
    assert row is not None
    assert (row.extras or {}).get(SCENES_KEY)
    assert "Athena" in row.instructions


async def start_onboarding(client: AsyncClient, token: str, onboarding: dict) -> str:
    created = await client.post(
        "/api/v1/assistant/sessions",
        json={"session_type": "onboarding", "extras": {"onboarding": onboarding}},
        headers=bearer(token),
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


async def test_voice_turned_on_mid_demo_opens_on_the_scene_on_screen(
    client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    """Turning voice on at the second scene must narrate that scene, not the introduction."""
    from app.features.assistant import repository

    token = await make_actor("assistant-onboarding-demo@example.com")
    scenes = (await client.get("/api/v1/assistant/onboarding-scenes", headers=bearer(token))).json()["scenes"]
    session_id = await start_onboarding(client, token, {"phase": "demo", "scene": 1})

    row = await repository.by_id(db_session, uuid.UUID(session_id))
    assert row is not None
    assert "This is a DEMO scenario." in row.instructions
    assert scenes[1]["patientLine"] in row.instructions
    assert "INTRODUCTION phase" not in row.instructions


async def test_an_onboarding_start_naming_no_real_scene_falls_back_to_the_introduction(
    client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    """The browser names a scene by position only, so it cannot hand the model a script."""
    from app.features.assistant import repository

    token = await make_actor("assistant-onboarding-bogus@example.com")
    bogus = ({"phase": "demo", "scene": 99}, {"phase": "exam", "scene": 0}, {"phase": "demo", "scene": "x"})
    for onboarding in bogus:
        session_id = await start_onboarding(client, token, onboarding)
        row = await repository.by_id(db_session, uuid.UUID(session_id))
        assert row is not None
        assert "INTRODUCTION phase" in row.instructions, onboarding


async def test_the_onboarding_scenes_are_offered_to_the_browser(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("assistant-scenes@example.com")

    response = await client.get("/api/v1/assistant/onboarding-scenes", headers=bearer(token))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["persona"]["assistantName"] == "Athena"
    assert body["scenes"]
    assert all(scene["patientLine"] and scene["question"] for scene in body["scenes"])
    # Without voice the walkthrough is read: each scene offers replies to pick
    # from and the answer Athena would model.
    assert all(len(scene["replies"]) >= 2 and scene["modelAnswer"] for scene in body["scenes"])


async def test_the_scenes_route_needs_somebody_signed_in(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/assistant/onboarding-scenes")).status_code == 401
