"""Env parsing helpers; ported from the legacy tests."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import pytest

from voice_infra.worker_config import (
    optional_agent_name,
    optional_load_threshold,
    optional_max_concurrent_jobs,
    required_agent_name,
    required_choice,
    validate_speech_credentials,
    worker_port,
)
from voice_infra.worker_load import concurrent_job_load_fnc, concurrent_job_load_settings


def test_required_agent_name_raises_when_unset(monkeypatch) -> None:
    monkeypatch.delenv("LIVEKIT_ASSESSMENT_AGENT_NAME", raising=False)
    with pytest.raises(RuntimeError, match="LIVEKIT_ASSESSMENT_AGENT_NAME"):
        required_agent_name("LIVEKIT_ASSESSMENT_AGENT_NAME")


def test_agent_name_is_stripped(monkeypatch) -> None:
    monkeypatch.setenv("LIVEKIT_ASSESSMENT_AGENT_NAME", "  assessment  ")
    assert optional_agent_name("LIVEKIT_ASSESSMENT_AGENT_NAME") == "assessment"
    assert required_agent_name("LIVEKIT_ASSESSMENT_AGENT_NAME") == "assessment"


def test_required_choice_normalises_and_rejects(monkeypatch) -> None:
    monkeypatch.setenv("OSCE_LIVEKIT_WORKER", " Assessment ")
    assert required_choice("OSCE_LIVEKIT_WORKER", ("assessment", "assistant")) == "assessment"
    monkeypatch.setenv("OSCE_LIVEKIT_WORKER", "patient")
    with pytest.raises(RuntimeError, match="'assessment', 'assistant'"):
        required_choice("OSCE_LIVEKIT_WORKER", ("assessment", "assistant"))


@pytest.mark.parametrize("configured", ["zero", "0", "65536"])
def test_worker_port_rejects_invalid_value(monkeypatch, configured: str) -> None:
    monkeypatch.setenv("PORT_VAR", configured)
    with pytest.raises(RuntimeError, match="PORT_VAR"):
        worker_port("PORT_VAR", 8085)


def test_worker_port_default_and_parse(monkeypatch) -> None:
    monkeypatch.delenv("PORT_VAR", raising=False)
    assert worker_port("PORT_VAR", 8085) == 8085
    monkeypatch.setenv("PORT_VAR", " 9000 ")
    assert worker_port("PORT_VAR", 8085) == 9000


@pytest.mark.parametrize("hosting", ["self-hosted", None, ""])
def test_speech_key_required_when_not_on_cloud(monkeypatch, hosting) -> None:
    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)
    monkeypatch.delenv("OSCE_LIVEKIT_HOSTING", raising=False)
    if hosting is not None:
        monkeypatch.setenv("OSCE_LIVEKIT_HOSTING", hosting)
    with pytest.raises(RuntimeError, match="DEEPGRAM_API_KEY"):
        validate_speech_credentials()
    monkeypatch.setenv("DEEPGRAM_API_KEY", "  dg  ")
    validate_speech_credentials()


def test_speech_key_not_required_on_cloud(monkeypatch) -> None:
    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)
    monkeypatch.setenv("OSCE_LIVEKIT_HOSTING", "cloud")
    validate_speech_credentials()


def test_max_concurrent_jobs_default_parse_and_disable(monkeypatch) -> None:
    monkeypatch.delenv("MAX_JOBS", raising=False)
    assert optional_max_concurrent_jobs("MAX_JOBS") is None
    assert optional_max_concurrent_jobs("MAX_JOBS", default=8) == 8
    monkeypatch.setenv("MAX_JOBS", "10")
    assert optional_max_concurrent_jobs("MAX_JOBS") == 10
    monkeypatch.setenv("MAX_JOBS", "off")
    assert optional_max_concurrent_jobs("MAX_JOBS", default=8) is None
    monkeypatch.setenv("MAX_JOBS", "many")
    with pytest.raises(RuntimeError, match="positive integer"):
        optional_max_concurrent_jobs("MAX_JOBS")


def test_load_threshold_default_and_bounds(monkeypatch) -> None:
    monkeypatch.delenv("THRESH", raising=False)
    assert optional_load_threshold("THRESH") == 0.99
    monkeypatch.setenv("THRESH", "1.5")
    with pytest.raises(RuntimeError, match="between 0 and 1"):
        optional_load_threshold("THRESH")


@dataclass
class _FakeWorker:
    active_jobs: list[str] = field(default_factory=list)


def test_load_fnc_scales_with_active_jobs() -> None:
    load = concurrent_job_load_fnc(8)
    worker = _FakeWorker(active_jobs=list("abcdefg"))
    assert load(worker) == 7 / 8
    worker.active_jobs.append("h")
    assert load(worker) == 1.0


def test_load_settings_default_cap_and_disable(monkeypatch) -> None:
    monkeypatch.delenv("MAX_JOBS", raising=False)
    monkeypatch.delenv("THRESH", raising=False)
    load, threshold = concurrent_job_load_settings(max_jobs_env="MAX_JOBS", threshold_env="THRESH")
    assert load is not None and threshold is not None
    assert threshold.prod_default == pytest.approx(0.99)
    assert threshold.dev_default == math.inf
    assert load(_FakeWorker(active_jobs=[str(i) for i in range(8)])) == 1.0
    monkeypatch.setenv("MAX_JOBS", "0")
    assert concurrent_job_load_settings(max_jobs_env="MAX_JOBS", threshold_env="THRESH") == (None, None)
