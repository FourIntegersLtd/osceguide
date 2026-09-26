"""Hosting glue: which worker a container runs, and that it runs as the container's own process."""

from __future__ import annotations

import json
import re
import sys
import types
from pathlib import Path

import pytest

from hosting import run_worker
from hosting.workers import WORKER_ENV, selected_worker

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_worker_is_selected_by_env(monkeypatch) -> None:
    monkeypatch.setenv(WORKER_ENV, "assessment")
    assert selected_worker().module == "livekit_assessment_worker.entrypoint"
    monkeypatch.setenv(WORKER_ENV, "assistant")
    assert selected_worker().module == "livekit_assistant_worker.entrypoint"


@pytest.mark.parametrize("value", ["", "patient", "both"])
def test_unknown_worker_fails_at_boot(monkeypatch, value) -> None:
    monkeypatch.setenv(WORKER_ENV, value)
    with pytest.raises(RuntimeError, match=WORKER_ENV):
        selected_worker()


def test_run_worker_runs_the_selected_worker_in_this_process(monkeypatch) -> None:
    """No subprocess: the selected entrypoint's CLI runs right here, so a stop
    signal sent to this process is the one the LiveKit SDK drains on."""
    calls_to_the_worker_cli: list[str] = []
    stand_in_entrypoint = types.ModuleType("livekit_assistant_worker.entrypoint")
    stand_in_entrypoint.cli_main = lambda: calls_to_the_worker_cli.append("assistant")
    monkeypatch.setitem(sys.modules, "livekit_assistant_worker.entrypoint", stand_in_entrypoint)
    monkeypatch.setenv(WORKER_ENV, "assistant")

    run_worker.cli_main()

    assert calls_to_the_worker_cli == ["assistant"]


def test_the_container_starts_the_worker_as_its_main_process() -> None:
    """The exec-form CMD makes Python PID 1, the process the kubelet sends SIGTERM to.

    A shell, make or gunicorn in between swallowed that signal: the worker never
    drained and kept taking new sessions until it was killed 15 minutes later.
    """
    dockerfile_text = (REPO_ROOT / "Dockerfile").read_text()
    command_lines = re.findall(r"^CMD (.+)$", dockerfile_text, flags=re.MULTILINE)
    assert [json.loads(command_line) for command_line in command_lines] == [
        ["python", "-m", "hosting.run_worker", "start"]
    ]
    assert "ENTRYPOINT" not in dockerfile_text
