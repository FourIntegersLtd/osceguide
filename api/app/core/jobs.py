"""Background jobs on procrastinate (Postgres-backed).

Why Postgres and not Redis: a job row is written in the same database, so a
service can enqueue "score this attempt" inside the transaction that marks the
transcript complete. Either both happen or neither does. Jobs survive deploys
and Redis restarts, and the queue is visible with plain SQL.

Each slice with background work declares its tasks inside a `register()`
function in its own `jobs.py`, so importing the module for its logic (which the
tests do) needs no configured queue. `get_jobs_app` builds the app and then
calls every slice's `register()`. That call is the whole mechanism: for a while
nothing made it, the worker started with an empty task set, and every job test
stayed green because each called the task's body directly.
"""

from __future__ import annotations

import importlib
import pkgutil

import procrastinate

from app.core.db import libpq_url
from app.core.settings import get_settings

_app: procrastinate.App | None = None


def discover_task_modules() -> list[str]:
    """Every `app.features.<slice>.jobs` module, imported."""
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


def _register_slice_tasks() -> None:
    for name in discover_task_modules():
        module = importlib.import_module(name)
        register = getattr(module, "register", None)
        if not callable(register):
            raise RuntimeError(
                f"{name} declares no register() function. Every jobs module must register "
                "its tasks in one, or the worker never sees them."
            )
        register()


def get_jobs_app() -> procrastinate.App:
    """The one procrastinate app, with every slice's tasks registered on it."""
    global _app
    if _app is None:
        settings = get_settings()
        app = procrastinate.App(
            connector=procrastinate.PsycopgConnector(conninfo=libpq_url(settings.database_url)),
        )
        # Assigned before the slices register: each `register()` fetches the
        # app through this function, so it has to be there already.
        _app = app
        try:
            _register_slice_tasks()
        except BaseException:
            _app = None
            raise
    return _app


def registered_task_names() -> set[str]:
    """Task names the worker will run, builtins excluded."""
    return {name for name in get_jobs_app().tasks if not name.startswith(("builtin:", "procrastinate."))}
