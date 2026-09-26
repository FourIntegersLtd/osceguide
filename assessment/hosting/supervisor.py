"""Self-hosted entry: gunicorn health endpoint + one worker subprocess.

A slimmer port of the legacy worker supervisor: one worker per container (chosen
by ``OSCE_LIVEKIT_WORKER``), restarted with back-off when it exits. ``/health``
answers 200 while the worker is starting or running and 503 once it has crashed,
so the platform waits through a cold boot and restarts a dead container.
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field

from hosting.workers import WorkerSpec, selected_worker

RESTART_BACKOFF_S = 5


@dataclass
class WorkerState:
    spec: WorkerSpec
    running: bool = False
    ever_started: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)

    def health(self, timestamp: float) -> dict[str, object]:
        if self.running:
            status = "running"
        elif self.ever_started:
            status = "crashed"
        else:
            status = "starting"
        return {"worker": self.spec.name, "status": status, "timestamp": timestamp}


def health_http_status(payload: dict[str, object]) -> int:
    return 503 if payload.get("status") == "crashed" else 200


def run_worker_forever(state: WorkerState, *, run=subprocess.run, sleep=time.sleep, max_runs: int | None = None) -> None:
    runs = 0
    while max_runs is None or runs < max_runs:
        runs += 1
        state.ever_started = True
        state.running = True
        try:
            result = run([sys.executable, "-m", state.spec.module, "start"], capture_output=False, timeout=None)
            code = result.returncode
        except Exception as exc:  # noqa: BLE001 — keep supervising
            code = f"exception: {exc}"
        finally:
            state.running = False
        print(f"[supervisor] {state.spec.name} worker exited ({code}); restarting in {RESTART_BACKOFF_S}s", flush=True)
        sleep(RESTART_BACKOFF_S)


_state: WorkerState | None = None
_started = False


def _start_once() -> WorkerState:
    global _state, _started
    if _state is None:
        _state = WorkerState(selected_worker())
    if not _started:
        _started = True
        threading.Thread(target=run_worker_forever, args=(_state,), daemon=True).start()
    return _state


def application(environ, start_response):
    state = _start_once()
    if environ.get("PATH_INFO", "/") in ("/", "/health"):
        payload = state.health(time.time())
        status = health_http_status(payload)
        start_response("503 Service Unavailable" if status == 503 else "200 OK", [("Content-Type", "application/json")])
        return [json.dumps(payload).encode()]
    start_response("404 Not Found", [("Content-Type", "text/plain")])
    return [b"Not Found"]
