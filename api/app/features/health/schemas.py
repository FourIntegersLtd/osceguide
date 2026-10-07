"""What the health and platform-console routes return."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

CheckState = Literal["ok", "error", "disabled"]


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "down"]
    version: str
    # The git commit this deploy was built from; empty when run locally.
    commit: str
    checks: dict[str, CheckState]


class JobEventRead(BaseModel):
    """One step of a job's history: `deferred`, `started`, `deferred_for_retry`, `failed`, …"""

    type: str
    at: datetime


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
    # Oldest first. procrastinate keeps no exception text; the error itself is
    # in the worker's log.
    events: list[JobEventRead] = []


class JobsPage(BaseModel):
    """Newest first, keyed on the job id; pass `next_before_id` back to continue."""

    items: list[JobRead]
    next_before_id: int | None = None


class PlatformHealth(HealthResponse):
    """The liveness report plus what only the console needs: the queue and the worker."""

    jobs_by_status: dict[str, int]
    worker_seen_at: datetime | None


class MachineryCapacity(BaseModel):
    """How full LiveKit Cloud, our own workers and the waiting line are, as the machinery page shows it.

    Declared here rather than borrowed from `voice`, so the two slices' contracts can change apart.
    None means Redis could not be asked; the self-hosted total is configuration, so always known.
    """

    overflow_enabled: bool
    max_concurrent: int
    active: int | None
    free: int | None
    self_hosted_seats_total: int
    self_hosted_seats_taken: int | None
    queue_length: int | None


class Machinery(BaseModel):
    """Everything the console's machinery page shows, as one frame of its stream.

    The same three read models the separate `GET` routes return, so the page
    keeps one set of types whether it reads them or is sent them.
    """

    health: PlatformHealth
    capacity: MachineryCapacity
    jobs: JobsPage
    # Which status `jobs` holds, so a page that just switched tabs can tell a
    # frame for the old tab from one for the new.
    job_status: str | None


class UndeliveredMessage(BaseModel):
    """An email the outbox gave up on after its last attempt, as the console lists it."""

    id: uuid.UUID
    recipient: str
    subject: str
    template_key: str
    attempts: int
    last_error: str | None
    abandoned_at: datetime
