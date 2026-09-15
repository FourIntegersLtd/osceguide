"""Background jobs on procrastinate (Postgres-backed).

Why Postgres and not Redis: a job row is written in the same database, so a
service can enqueue "score this attempt" inside the transaction that marks the
transcript complete. Either both happen or neither does. Jobs survive deploys
and Redis restarts, and the queue is visible with plain SQL.

Each slice that has background work declares tasks in its own `jobs.py`; the
worker process discovers them by module path.
"""

from __future__ import annotations

import importlib
import pkgutil

import procrastinate

from app.core.db import libpq_url
from app.core.settings import get_settings

_app: procrastinate.App | None = None


def discover_task_modules() -> list[str]:
    features = importlib.import_module("app.features")
    found: list[str] = []
    for module_info in pkgutil.iter_modules(features.__path__):
        candidate = f"app.features.{module_info.name}.jobs"
        try:
            importlib.import_module(candidate)
        except ModuleNotFoundError as exc:
            if exc.name != candidate:
                raise
            continue
        found.append(candidate)
    return found


def get_jobs_app() -> procrastinate.App:
    global _app
    if _app is None:
        settings = get_settings()
        _app = procrastinate.App(
            connector=procrastinate.PsycopgConnector(conninfo=libpq_url(settings.database_url)),
            import_paths=discover_task_modules(),
        )
    return _app
