"""The workers this image can run, selected by ``OSCE_LIVEKIT_WORKER``."""

from __future__ import annotations

import os
from dataclasses import dataclass

WORKER_ENV = "OSCE_LIVEKIT_WORKER"


@dataclass(frozen=True)
class WorkerSpec:
    """One worker: its name and the module whose ``cli_main`` runs it.

    Each module owns its own HTTP port (``PORT_ENV`` in the entrypoint), where
    the LiveKit SDK serves ``/`` for the K8s probes.
    """

    name: str
    module: str


WORKERS: dict[str, WorkerSpec] = {
    "assessment": WorkerSpec("assessment", "livekit_assessment_worker.entrypoint"),
    "assistant": WorkerSpec("assistant", "livekit_assistant_worker.entrypoint"),
}


def selected_worker() -> WorkerSpec:
    """The worker named by ``OSCE_LIVEKIT_WORKER``; refuses to boot on any other value."""
    worker_name = (os.environ.get(WORKER_ENV) or "").strip()
    if worker_name not in WORKERS:
        raise RuntimeError(f"{WORKER_ENV} must be one of {sorted(WORKERS)} (got {worker_name!r})")
    return WORKERS[worker_name]
