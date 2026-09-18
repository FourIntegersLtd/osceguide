"""The real LiveKit adapter, against the real SDK.

This file exists because the SDK was a dependency of nothing: `adapter.py`
imports it inside each call and turns an ImportError into `VoiceUnavailable`,
so every test passed and no deployment could mint a token. With `livekit-api`
declared, the adapter can be held to what the worker and the browser expect.
"""

from __future__ import annotations

import json
from collections.abc import Iterator

import jwt
import pytest

from app.core.settings import get_settings
from app.features.voice.adapter import LiveKitTokens
from app.features.voice.errors import VoiceUnavailable

SECRET = "a-livekit-secret-that-is-long-enough"


@pytest.fixture
def livekit_configured(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("LIVEKIT_API_KEY", "devkey")
    monkeypatch.setenv("LIVEKIT_API_SECRET", SECRET)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _claims(token: str) -> dict:
    return jwt.decode(token, SECRET, algorithms=["HS256"], options={"verify_aud": False})


def test_a_candidate_token_joins_one_room_as_itself(livekit_configured: None) -> None:
    token = LiveKitTokens().issue(
        identity="candidate-1", room="circuit_abc", agent_name=None, dispatch_metadata=None
    )

    claims = _claims(token)
    assert claims["sub"] == "candidate-1"
    assert claims["iss"] == "devkey"
    assert claims["video"]["room"] == "circuit_abc"
    assert claims["video"]["roomJoin"] is True
    assert claims["video"]["canPublish"] is True
    assert claims["video"]["roomAdmin"] is False


def test_a_token_with_no_agent_name_summons_nobody(livekit_configured: None) -> None:
    """The circuit dispatches its own patient; a join token must not."""
    token = LiveKitTokens().issue(
        identity="candidate-1", room="circuit_abc", agent_name=None, dispatch_metadata=None
    )

    assert "roomConfig" not in _claims(token)


def test_an_agent_name_rides_into_the_room_on_the_token(livekit_configured: None) -> None:
    token = LiveKitTokens().issue(
        identity="candidate-1",
        room="practice_1",
        agent_name="patient",
        dispatch_metadata={"attempt_id": "a-1"},
    )

    dispatch = _claims(token)["roomConfig"]["agents"][0]
    assert dispatch["agentName"] == "patient"
    assert json.loads(dispatch["metadata"]) == {"attempt_id": "a-1"}


def test_an_observer_can_neither_speak_nor_type(livekit_configured: None) -> None:
    """An examiner watches and listens. Data counts as speaking."""
    token = LiveKitTokens().issue(
        identity="observer-9",
        room="circuit_abc",
        agent_name=None,
        dispatch_metadata=None,
        can_publish=False,
    )

    video = _claims(token)["video"]
    assert video["canPublish"] is False
    assert video["canPublishData"] is False
    assert video["canSubscribe"] is True


def test_a_token_expires(livekit_configured: None) -> None:
    claims = _claims(
        LiveKitTokens().issue(
            identity="candidate-1",
            room="circuit_abc",
            agent_name=None,
            dispatch_metadata=None,
            ttl_seconds=90,
        )
    )

    assert claims["exp"] - claims["nbf"] == 90


def test_without_credentials_voice_is_unavailable_rather_than_broken(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "")
    get_settings.cache_clear()
    try:
        with pytest.raises(VoiceUnavailable):
            LiveKitTokens().issue(
                identity="candidate-1", room="circuit_abc", agent_name=None, dispatch_metadata=None
            )
    finally:
        get_settings.cache_clear()
