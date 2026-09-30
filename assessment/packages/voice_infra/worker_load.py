"""Per-worker concurrent session caps for self-hosted workers."""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

from livekit.agents.worker import ServerEnvOption

from .worker_config import optional_load_threshold, optional_max_concurrent_jobs


def concurrent_job_load_fnc(max_jobs: int) -> Callable[[Any], float]:
    """Load in [0, 1] from active job count versus ``max_jobs``."""

    def load_fnc(worker: Any) -> float:
        return min(1.0, len(worker.active_jobs) / max_jobs)

    return load_fnc


def concurrent_job_load_threshold(prod_default: float) -> ServerEnvOption[float]:
    """No cap in dev; ``prod_default`` in production."""
    return ServerEnvOption(dev_default=math.inf, prod_default=prod_default)


def concurrent_job_load_settings(
    *,
    max_jobs_env: str,
    threshold_env: str,
    default_max_jobs: int = 8,
    default_threshold: float = 0.99,
) -> tuple[Callable[[Any], float] | None, ServerEnvOption[float] | None]:
    """Session cap from env, or ``(None, None)`` when disabled. Ignored on LiveKit Cloud."""
    max_jobs = optional_max_concurrent_jobs(max_jobs_env, default=default_max_jobs)
    if max_jobs is None:
        return None, None
    threshold = optional_load_threshold(threshold_env, default=default_threshold)
    return concurrent_job_load_fnc(max_jobs), concurrent_job_load_threshold(threshold)
