"""The workers this image can run, selected by ``OSCE_LIVEKIT_WORKER``."""

from __future__ import annotations

import os
from dataclasses import dataclass

WORKER_ENV = "OSCE_LIVEKIT_WORKER"


@dataclass(frozen=True)
class WorkerSpec:
    name: str
    module: str          # ``python -m <module> start``
    port_env: str
    default_port: int


WORKERS: dict[str, WorkerSpec] = {
    "assessment": WorkerSpec("assessment", "livekit_assessment_worker.entrypoint", "LIVEKIT_ASSESSMENT_WORKER_PORT", 8087),
    "assistant": WorkerSpec("assistant", "livekit_assistant_worker.entrypoint", "LIVEKIT_ASSISTANT_WORKER_PORT", 8088),
}


def selected_worker() -> WorkerSpec:
    name = (os.environ.get(WORKER_ENV) or "").strip()
    if name not in WORKERS:
        raise RuntimeError(f"{WORKER_ENV} must be one of {sorted(WORKERS)} (got {name!r})")
    return WORKERS[name]
