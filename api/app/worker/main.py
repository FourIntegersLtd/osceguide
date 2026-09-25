"""Background worker entrypoint: `python -m app.worker.main`.

Runs every task declared in `app/features/*/jobs.py`. Scale by running more
replicas of this process; each takes jobs with SKIP LOCKED so they never
double-run.

This process is load-bearing for live examinations, not only for marking: a
circuit's transitions are jobs, so a deployment with no worker running has
examinations that start and never move.
"""

from __future__ import annotations

import procrastinate

from app.core.db import import_all_models
from app.core.jobs import get_jobs_app
from app.core.logging import configure_logging, get_logger
from app.core.settings import get_settings


def build_worker_app() -> procrastinate.App:
    """The job app, with every model imported first.

    Importing the tasks is not enough: a slice's `jobs.py` pulls in its own models and
    no others, so a mapper whose foreign key names a table nothing imported cannot be
    configured. Order-dependent otherwise, which is worse than reliably broken —
    `import_all_models` closes it for the worker the way it already does for Alembic.

    Separate from `main()` so a test can assert the mappers configure without starting
    a worker.
    """
    import_all_models()
    return get_jobs_app()


def main() -> None:
    settings = get_settings()
    configure_logging(settings)
    app = build_worker_app()
    get_logger(__name__).info(
        "worker starting", concurrency=settings.worker_concurrency, tasks=list(app.tasks)
    )
    app.run_worker(
        concurrency=settings.worker_concurrency,
        # Circuit transitions are scheduled for a future moment, and a
        # scheduled job is found by polling rather than by notification.
        fetch_job_polling_interval=settings.worker_fetch_job_polling_seconds,
    )


if __name__ == "__main__":
    main()
