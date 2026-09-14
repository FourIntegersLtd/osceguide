"""Hosting glue: worker selection, health semantics, restart loop."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from hosting import supervisor
from hosting.workers import WORKER_ENV, selected_worker


def test_worker_is_selected_by_env(monkeypatch) -> None:
    monkeypatch.setenv(WORKER_ENV, "assessment")
    spec = selected_worker()
    assert spec.module == "livekit_assessment_worker.entrypoint"
    assert spec.default_port == 8087


@pytest.mark.parametrize("value", ["", "patient", "both"])
def test_unknown_worker_fails_at_boot(monkeypatch, value) -> None:
    monkeypatch.setenv(WORKER_ENV, value)
    with pytest.raises(RuntimeError, match=WORKER_ENV):
        selected_worker()


def test_health_is_200_while_starting_or_running_and_503_after_a_crash(monkeypatch) -> None:
    monkeypatch.setenv(WORKER_ENV, "assessment")
    state = supervisor.WorkerState(selected_worker())
    assert supervisor.health_http_status(state.health(0)) == 200
    state.ever_started = True
    state.running = True
    assert state.health(0)["status"] == "running"
    state.running = False
    assert supervisor.health_http_status(state.health(0)) == 503


def test_restart_loop_relaunches_the_worker_module(monkeypatch) -> None:
    monkeypatch.setenv(WORKER_ENV, "assessment")
    state = supervisor.WorkerState(selected_worker())
    commands, sleeps = [], []

    def run(cmd, **_):
        commands.append(cmd)
        return SimpleNamespace(returncode=1)

    supervisor.run_worker_forever(state, run=run, sleep=sleeps.append, max_runs=2)
    assert [c[1:] for c in commands] == [["-m", "livekit_assessment_worker.entrypoint", "start"]] * 2
    assert sleeps == [5, 5]
    assert state.ever_started and not state.running
