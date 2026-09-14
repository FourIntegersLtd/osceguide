"""The worker fetches a rendered attempt; it never fetches a station."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from livekit_assessment_worker import bootstrap as bootstrap_module
from livekit_assessment_worker.bootstrap import BootstrapError, fetch_bootstrap, parse_bootstrap
from livekit_assessment_worker.metadata import DispatchMetadata
from voice_infra import BackendEndpoints
from voice_infra.backend_http import SyncGetResult

ENDPOINTS = BackendEndpoints(
    label="practice", base_url_env="PRACTICE_URL", secret_env="PRACTICE_SECRET", secret_header="X-Practice-Secret",
    slot_release_path="/r", slot_extend_path="/e", slot_payload_key="room_name",
)
METADATA = DispatchMetadata(attempt_id="attempt-1", backend="practice", candidate_ref="candidate-42")


@pytest.fixture
def rendered_attempt(attempt):
    profile = attempt.definition.interaction_profile.model_copy(update={"instructions": "You are the patient."})
    return attempt.model_copy(update={"definition": attempt.definition.model_copy(update={"interaction_profile": profile})})


@pytest.fixture
def payload(rendered_attempt, scenario) -> dict:
    return {"attempt": rendered_attempt.model_dump(mode="json"), "scenario": scenario.model_dump(mode="json")}


def test_parse_round_trips_attempt_and_scenario(payload, rendered_attempt, scenario) -> None:
    result = parse_bootstrap(payload)
    assert result.attempt == rendered_attempt
    assert result.scenario == scenario


def test_unrendered_instructions_are_refused(attempt, scenario) -> None:
    with pytest.raises(BootstrapError, match="no rendered instructions"):
        parse_bootstrap({"attempt": attempt.model_dump(mode="json"), "scenario": scenario.model_dump(mode="json")})


@pytest.mark.parametrize("bad", [None, [], {"attempt": {}}, {"scenario": {}}])
def test_malformed_payloads_are_refused(bad) -> None:
    with pytest.raises(BootstrapError):
        parse_bootstrap(bad)


def _get(result: SyncGetResult):
    return patch.object(bootstrap_module, "sync_get_json", return_value=result)


def test_fetch_uses_the_backend_url_secret_and_attempt_path(monkeypatch, payload) -> None:
    monkeypatch.setenv("PRACTICE_URL", "https://api.test")
    monkeypatch.setenv("PRACTICE_SECRET", "s3cret")
    with _get(SyncGetResult(ok=True, status=200, data=payload)) as get:
        result = fetch_bootstrap(ENDPOINTS, METADATA)
    assert result.attempt.attempt_id == "attempt-1"
    args, kwargs = get.call_args
    assert args == ("https://api.test", "/api/worker/attempts/attempt-1")
    assert kwargs["headers"] == {"X-Practice-Secret": "s3cret"}


def test_auth_failure_is_reported_as_such(monkeypatch) -> None:
    monkeypatch.setenv("PRACTICE_URL", "https://api.test")
    with _get(SyncGetResult(ok=False, status=401, data=None, auth_failed=True)):
        with pytest.raises(BootstrapError, match="rejected worker credentials") as info:
            fetch_bootstrap(ENDPOINTS, METADATA)
    assert info.value.auth_failed is True


def test_unavailable_attempt_names_the_backend(monkeypatch) -> None:
    monkeypatch.setenv("PRACTICE_URL", "https://api.test")
    with _get(SyncGetResult(ok=False, status=404, data=None)):
        with pytest.raises(BootstrapError, match="unavailable from 'practice' \\(HTTP 404\\)"):
            fetch_bootstrap(ENDPOINTS, METADATA)


def test_a_different_attempt_than_dispatched_is_refused(monkeypatch, payload) -> None:
    monkeypatch.setenv("PRACTICE_URL", "https://api.test")
    payload["attempt"]["attempt_id"] = "someone-elses"
    with _get(SyncGetResult(ok=True, status=200, data=payload)):
        with pytest.raises(BootstrapError, match="different attempt"):
            fetch_bootstrap(ENDPOINTS, METADATA)


def test_missing_base_url_fails_before_any_request(monkeypatch) -> None:
    monkeypatch.delenv("PRACTICE_URL", raising=False)
    with _get(SyncGetResult(ok=True, status=200, data={})) as get:
        with pytest.raises(Exception):
            fetch_bootstrap(ENDPOINTS, METADATA)
    get.assert_not_called()
