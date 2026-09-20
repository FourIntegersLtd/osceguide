"""Background worker entrypoint: `python -m app.worker.main`.

Runs every task declared in `app/features/*/jobs.py`. Scale by running more
replicas of this process; each takes jobs with SKIP LOCKED so they never
double-run.
"""

from __future__ import annotations

from app.core.jobs import get_jobs_app
from app.core.logging import configure_logging, get_logger
from app.core.settings import get_settings


def _register_slice_tasks() -> None:
    """Bind procrastinate tasks declared in each slice's `register()`.

    Import paths alone do not run those functions; without this call the worker
    only sees built-in housekeeping tasks and scoring jobs fail with "task not
    found".
    """
    import importlib

    from app.core.jobs import discover_task_modules

    for module_path in discover_task_modules():
        module = importlib.import_module(module_path)
        register = getattr(module, "register", None)
        if callable(register):
            register()


def main() -> None:
    settings = get_settings()
    configure_logging(settings)
    app = get_jobs_app()
    _register_slice_tasks()
    get_logger(__name__).info(
        "worker starting", concurrency=settings.worker_concurrency, tasks=list(app.tasks)
    )
    app.run_worker(concurrency=settings.worker_concurrency)


if __name__ == "__main__":
    main()
