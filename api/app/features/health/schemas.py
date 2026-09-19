from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

CheckState = Literal["ok", "error", "disabled"]


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "down"]
    version: str
    checks: dict[str, CheckState]


class JobRead(BaseModel):
    """One queued job as procrastinate holds it."""

    id: int
    queue_name: str
    task_name: str
    status: str
    attempts: int
    scheduled_at: datetime | None
    args: dict[str, Any]
    queueing_lock: str | None


class JobsPage(BaseModel):
    """Newest first, keyed on the job id; pass `next_before_id` back to continue."""

    items: list[JobRead]
    next_before_id: int | None = None


class PlatformHealth(HealthResponse):
    """The liveness report plus what only the console needs: the queue and the worker."""

    jobs_by_status: dict[str, int]
    worker_seen_at: datetime | None
