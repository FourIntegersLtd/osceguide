"""Worker options are built from environment only, failing fast when misconfigured."""

from __future__ import annotations

import json

import pytest

from livekit_assessment_worker import entrypoint
from voice_infra.config import BACKENDS_ENV

SPEC = {"practice": {"base_url_env": "PRACTICE_URL", "secret_env": "PRACTICE_SECRET", "secret_header": "X-Practice-Secret",
                     "slot_release_path": "/r", "slot_extend_path": "/e", "slot_payload_key": "room_name"}}


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv(BACKENDS_ENV, json.dumps(SPEC))
    monkeypatch.setenv("DEEPGRAM_API_KEY", "dg")
    monkeypatch.setenv(entrypoint.AGENT_NAME_ENV, "assessment-self-hosted")
    monkeypatch.setenv(entrypoint.PORT_ENV, "9001")
    monkeypatch.setenv(entrypoint.MAX_JOBS_ENV, "3")


def test_options_come_from_env(configured) -> None:
    options = entrypoint.build_worker_options()
    assert options.agent_name == "assessment-self-hosted"
    assert options.port == 9001
    assert options.load_fnc is not None


def test_missing_backends_fail_fast(configured, monkeypatch) -> None:
    monkeypatch.delenv(BACKENDS_ENV)
    with pytest.raises(Exception, match=BACKENDS_ENV):
        entrypoint.build_worker_options()


def test_missing_speech_key_fails_fast(configured, monkeypatch) -> None:
    monkeypatch.delenv("DEEPGRAM_API_KEY")
    with pytest.raises(Exception, match="DEEPGRAM_API_KEY"):
        entrypoint.build_worker_options()
