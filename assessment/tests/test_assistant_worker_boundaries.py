"""The assistant worker never loads the assessment engine's runtime or evaluation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from livekit_assistant_worker import entrypoint
from voice_infra.config import BACKENDS_ENV

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = ("osce_assessment.runtime", "osce_assessment.evaluation", "osce_assessment.schemas", "livekit_assessment_worker")


def test_importing_the_assistant_worker_loads_no_assessment_machinery() -> None:
    code = (
        "import sys\nimport livekit_assistant_worker.session, livekit_assistant_worker.entrypoint\n"
        f"print(sorted(m for m in sys.modules if m.startswith({FORBIDDEN!r})))\n"
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT, env={"PYTHONPATH": "packages", "PATH": ""})
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "[]"


def test_worker_options_come_from_env(monkeypatch) -> None:
    monkeypatch.setenv(BACKENDS_ENV, '{"practice": {"base_url_env": "P_URL", "secret_env": "P_SECRET", "secret_header": "X-S", "slot_release_path": "/r", "slot_extend_path": "/e", "slot_payload_key": "room_name"}}')
    monkeypatch.setenv("DEEPGRAM_API_KEY", "dg")
    monkeypatch.setenv("OSCE_LIVEKIT_HOSTING", "self-hosted")
    monkeypatch.setenv(entrypoint.AGENT_NAME_ENV, "assistant-self-hosted")
    options = entrypoint.build_worker_options()
    assert options.agent_name == "assistant-self-hosted" and options.port == 8088 and options.prewarm_fnc is entrypoint.prewarm
    monkeypatch.delenv(entrypoint.AGENT_NAME_ENV)
    with pytest.raises(Exception, match=entrypoint.AGENT_NAME_ENV):
        entrypoint.build_worker_options()


def test_missing_speech_key_fails_fast(monkeypatch) -> None:
    monkeypatch.setenv(BACKENDS_ENV, '{"practice": {"base_url_env": "P_URL", "secret_env": "P_SECRET", "secret_header": "X-S", "slot_release_path": "/r", "slot_extend_path": "/e", "slot_payload_key": "room_name"}}')
    monkeypatch.setenv("OSCE_LIVEKIT_HOSTING", "self-hosted")
    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)
    with pytest.raises(Exception, match="DEEPGRAM_API_KEY"):
        entrypoint.validate_environment()


def test_hosting_knows_the_assistant_worker(monkeypatch) -> None:
    from hosting.workers import WORKER_ENV, selected_worker

    monkeypatch.setenv(WORKER_ENV, "assistant")
    assert selected_worker().module == "livekit_assistant_worker.entrypoint"
