"""Backends are configuration, looked up by an opaque label."""

from __future__ import annotations

import json

import pytest

from voice_infra import BackendEndpoints, BackendRegistry, BackendRegistryError
from voice_infra.config import BACKENDS_ENV

SPEC = {
    "practice": {
        "base_url_env": "PRACTICE_URL",
        "secret_env": "PRACTICE_SECRET",
        "secret_header": "X-Practice-Secret",
        "slot_release_path": "/api/worker/livekit-cloud-slot/release",
        "slot_extend_path": "/api/worker/livekit-cloud-slot/extend",
        "slot_payload_key": "room_name",
    },
    "institution": {
        "base_url_env": "INSTITUTION_URL",
        "secret_env": "INSTITUTION_SECRET",
        "secret_header": "X-Institution-Secret",
        "slot_release_path": "/api/org/worker/livekit-cloud-slot/release",
        "slot_extend_path": "/api/org/worker/livekit-cloud-slot/extend",
        "slot_payload_key": "roomName",
        "attempt_path": "/api/org/worker/attempts/{attempt_id}",
        "transcript_chunks_path": "/api/org/worker/attempts/{attempt_id}/transcript-chunks",
        "transcript_path": "/api/org/worker/attempts/{attempt_id}/transcript",
    },
}


@pytest.fixture
def registry(monkeypatch) -> BackendRegistry:
    monkeypatch.setenv(BACKENDS_ENV, json.dumps(SPEC))
    for var in ("PRACTICE_URL", "PRACTICE_SECRET", "INSTITUTION_URL", "INSTITUTION_SECRET"):
        monkeypatch.delenv(var, raising=False)
    return BackendRegistry.from_env()


def test_registry_parses_labels_and_specs(registry: BackendRegistry) -> None:
    assert registry.labels() == ("practice", "institution")
    practice = registry.get("practice")
    assert isinstance(practice, BackendEndpoints)
    assert practice.label == "practice"
    assert practice.slot_payload_key == "room_name"


def test_unknown_label_names_the_configured_ones(registry: BackendRegistry) -> None:
    with pytest.raises(BackendRegistryError, match="unknown backend 'employer'.*institution.*practice"):
        registry.get("employer")


def test_urls_and_secrets_are_read_from_env_at_call_time(registry: BackendRegistry, monkeypatch) -> None:
    practice = registry.get("practice")
    assert practice.base_url() is None
    assert practice.secret_headers() == {}
    assert practice.slot_endpoint("release") is None
    monkeypatch.setenv("PRACTICE_URL", "https://api.test/")
    monkeypatch.setenv("PRACTICE_SECRET", " s3cret ")
    assert practice.base_url() == "https://api.test"
    assert practice.secret_headers() == {"X-Practice-Secret": "s3cret"}
    assert practice.slot_endpoint("release") == "https://api.test/api/worker/livekit-cloud-slot/release"
    assert practice.slot_endpoint("extend") == "https://api.test/api/worker/livekit-cloud-slot/extend"
    assert practice.url("/api/worker/sessions/x") == "https://api.test/api/worker/sessions/x"


def test_payload_key_is_per_backend(registry: BackendRegistry) -> None:
    assert registry.get("practice").slot_payload("r") == {"room_name": "r"}
    assert registry.get("institution").slot_payload("r") == {"roomName": "r"}


def test_attempt_routes_default_when_absent_and_are_per_backend_when_declared(registry: BackendRegistry, monkeypatch) -> None:
    """A backend mounted under a prefix declares its own worker routes; one without keeps the defaults."""
    monkeypatch.setenv("PRACTICE_URL", "https://practice.test")
    monkeypatch.setenv("INSTITUTION_URL", "https://org.test/")
    practice, institution = registry.get("practice"), registry.get("institution")
    assert practice.attempt_url("a-1") == "https://practice.test/api/worker/attempts/a-1"
    assert practice.transcript_chunks_url("a-1") == "https://practice.test/api/worker/attempts/a-1/transcript-chunks"
    assert practice.transcript_url("a-1") == "https://practice.test/api/worker/attempts/a-1/transcript"
    assert institution.attempt_url("s-1") == "https://org.test/api/org/worker/attempts/s-1"
    assert institution.transcript_chunks_url("s-1") == "https://org.test/api/org/worker/attempts/s-1/transcript-chunks"
    assert institution.transcript_url("s-1") == "https://org.test/api/org/worker/attempts/s-1/transcript"


def test_a_route_without_the_attempt_placeholder_is_rejected(monkeypatch) -> None:
    spec = {"practice": {**SPEC["practice"], "transcript_path": "/api/worker/transcript"}}
    monkeypatch.setenv(BACKENDS_ENV, json.dumps(spec))
    with pytest.raises(BackendRegistryError, match="transcript_path must contain {attempt_id}"):
        BackendRegistry.from_env()


def test_required_base_url_names_the_variable(registry: BackendRegistry) -> None:
    with pytest.raises(BackendRegistryError, match="INSTITUTION_URL must be set for backend 'institution'"):
        registry.get("institution").required_base_url()


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ("", "must be set"),
        ("not json", "not valid JSON"),
        ("[]", "non-empty JSON object"),
        ("{}", "non-empty JSON object"),
        ('{"x": "nope"}', "must be an object"),
        ('{"x": {"base_url_env": "A"}}', "missing"),
    ],
)
def test_malformed_configuration_is_rejected(monkeypatch, raw: str, message: str) -> None:
    monkeypatch.setenv(BACKENDS_ENV, raw)
    with pytest.raises(BackendRegistryError, match=message):
        BackendRegistry.from_env()
