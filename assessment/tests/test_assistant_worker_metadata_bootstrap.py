"""Dispatch metadata and the bootstrap contract for assistant sessions."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from livekit_assistant_worker import bootstrap as bootstrap_module
from livekit_assistant_worker.bootstrap import AssistantSession, BootstrapError, fetch_bootstrap, fetch_scene_instructions, parse_bootstrap
from livekit_assistant_worker.metadata import DispatchMetadata, MetadataError, parse_dispatch_metadata
from voice_infra import BackendEndpoints
from voice_infra.backend_http import SyncGetResult

ENDPOINTS = BackendEndpoints(label="practice", base_url_env="PRACTICE_URL", secret_env="PRACTICE_SECRET", secret_header="X-S", slot_release_path="/r", slot_extend_path="/e", slot_payload_key="room_name")


def test_metadata_accepts_both_spellings_and_requires_session_and_backend(monkeypatch) -> None:
    monkeypatch.setenv("PRACTICE_URL", "https://api.test")
    assert parse_dispatch_metadata(json.dumps({"sessionId": "unified_1", "backend": "practice", "candidateRef": "u1"})) == DispatchMetadata("unified_1", "practice", "u1")
    assert ENDPOINTS.assistant_bootstrap_url("s") == "https://api.test/api/worker/assistant-sessions/s"
    with pytest.raises(MetadataError):
        parse_dispatch_metadata('{"backend": "b"}')
    with pytest.raises(MetadataError):
        parse_dispatch_metadata("nope")


def test_bootstrap_parses_every_mode_and_ignores_unknown_keys() -> None:
    session = parse_bootstrap({"session": {"session_id": "s", "worker_type": "help", "candidate_ref": "u1", "instructions": "Help.", "extras": {"screen_ui_guidance": True, "voice_help_intent": "guide", "app_type": "sca"}, "app_type": "sca",
                                           "help_corpus": {"entries": []},  # older backends still send this; it is ignored
                                           "gpt_live": {"voice": "v", "backend": "b", "opening": "o"}}})
    assert isinstance(session, AssistantSession)
    assert session.extras.screen_ui_guidance is True and session.extras.voice_help_intent == "guide"
    assert session.greeting is None and session.gpt_live.opening == "o" and not hasattr(session, "help_corpus")
    dashboard = parse_bootstrap({"session": {"session_id": "s", "worker_type": "dashboard", "instructions": "Rendered by the backend."}})
    assert dashboard.instructions == "Rendered by the backend." and dashboard.gpt_live is None


@pytest.mark.parametrize("bad", [
    None, {}, {"session": {"session_id": "s", "worker_type": "conversation", "instructions": "x"}}, {"session": {"worker_type": "help", "instructions": "x"}},
    {"session": {"session_id": "s", "worker_type": "help"}},  # every mode arrives rendered
    {"session": {"session_id": "s", "worker_type": "consulting-doctor", "instructions": "  "}},
    {"session": {"session_id": "s", "worker_type": "athena-doctor", "instructions": "x"}},  # a persona is not a session type
    {"session": {"session_id": "s", "worker_type": "help", "instructions": "x", "gpt_live": {"voice": "v"}}},
])
def test_malformed_or_assessment_sessions_are_refused(bad) -> None:
    with pytest.raises(BootstrapError):
        parse_bootstrap(bad)


def test_fetch_uses_the_backend_and_checks_the_session_id(monkeypatch) -> None:
    monkeypatch.setenv("PRACTICE_URL", "https://api.test")
    monkeypatch.setenv("PRACTICE_SECRET", "s")
    payload = {"session": {"session_id": "unified_1", "worker_type": "help", "instructions": "Help."}}
    with patch.object(bootstrap_module, "sync_get_json_url", return_value=SyncGetResult(ok=True, status=200, data=payload)) as get:
        assert fetch_bootstrap(ENDPOINTS, DispatchMetadata("unified_1", "practice")).worker_type == "help"
    assert get.call_args.args == ("https://api.test/api/worker/assistant-sessions/unified_1",)
    assert get.call_args.kwargs["headers"] == {"X-S": "s"}
    with patch.object(bootstrap_module, "sync_get_json_url", return_value=SyncGetResult(ok=True, status=200, data=payload)):
        with pytest.raises(BootstrapError, match="different session"):
            fetch_bootstrap(ENDPOINTS, DispatchMetadata("other", "practice"))
    with patch.object(bootstrap_module, "sync_get_json_url", return_value=SyncGetResult(ok=False, status=401, data=None, auth_failed=True)):
        with pytest.raises(BootstrapError, match="credentials"):
            fetch_bootstrap(ENDPOINTS, DispatchMetadata("unified_1", "practice"))


def test_scene_instructions_are_fetched_from_the_backend(monkeypatch) -> None:
    monkeypatch.setenv("PRACTICE_URL", "https://api.test")
    monkeypatch.setenv("PRACTICE_SECRET", "s")
    scene = {"phase": "demo", "question": "Q?", "patientLine": "Line"}
    with patch.object(bootstrap_module, "sync_post_json_url", return_value=SyncGetResult(ok=True, status=200, data={"instructions": "Demo scene."})) as post:
        assert fetch_scene_instructions(ENDPOINTS, "unified_1", scene) == "Demo scene."
    assert post.call_args.args == ("https://api.test/api/worker/assistant-sessions/unified_1/scene", scene)
    assert post.call_args.kwargs["headers"] == {"X-S": "s"}
    with patch.object(bootstrap_module, "sync_post_json_url", return_value=SyncGetResult(ok=True, status=200, data={"instructions": ""})):
        with pytest.raises(BootstrapError, match="scene instructions unavailable"):
            fetch_scene_instructions(ENDPOINTS, "unified_1", scene)
