"""The worker runs the tasks the slices declare.

The one test that would have caught the worker starting with no tasks at all:
every job test called the task body directly, so `register()` going uncalled
was invisible. This asks the app itself.
"""

from __future__ import annotations

import pathlib

import procrastinate

from app.core import jobs

ROOT = pathlib.Path(__file__).resolve().parents[2]

FEATURE_TASKS = {
    "score_attempt",
    "deliver_outbound_messages",
    "match_practice_queue",
    "suspend_lapsed_organizations",
    # The examination bell. Unregistered, a circuit starts and never moves —
    # which is the failure this whole file exists to make impossible.
    "advance_circuit",
    "sweep_circuits",
    # The tutor's memory. Unregistered, a dashboard conversation is stored and
    # never summarised — so the turns are kept forever and the tutor learns
    # nothing, which is both halves of the failure at once.
    "summarise_assistant_session",
    "summarise_debrief",
    # Unregistered, `search_material` answers out of an index that is never
    # rebuilt — so the tutor goes on quoting material that was edited or
    # withdrawn, with a citation to a page that no longer says it.
    "reindex_material",
}
PERIODIC_TASKS = {
    "deliver_outbound_messages",
    "match_practice_queue",
    "suspend_lapsed_organizations",
    "sweep_circuits",
    "reindex_material",
}


def test_every_slice_task_is_registered_with_the_worker() -> None:
    assert jobs.registered_task_names() >= FEATURE_TASKS


def test_the_periodic_tasks_are_scheduled() -> None:
    app = jobs.get_jobs_app()
    scheduled = {periodic.task.name for periodic in app.periodic_registry.periodic_tasks.values()}
    assert scheduled >= PERIODIC_TASKS


def test_the_app_is_built_once() -> None:
    assert jobs.get_jobs_app() is jobs.get_jobs_app()


def test_every_jobs_module_has_a_register_function() -> None:
    import importlib

    for name in jobs.discover_task_modules():
        assert callable(getattr(importlib.import_module(name), "register", None)), name


def test_a_jobs_module_without_register_is_refused(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Plant the violation: a module that defines tasks nowhere."""
    monkeypatch.setattr(jobs, "_app", None)
    monkeypatch.setattr(jobs, "discover_task_modules", lambda: ["tests.unit.test_jobs_registry"])
    try:
        jobs.get_jobs_app()
    except RuntimeError as exc:
        assert "register()" in str(exc)
        assert jobs._app is None
    else:
        raise AssertionError("a jobs module with no register() was accepted")
    monkeypatch.undo()
    assert isinstance(jobs.get_jobs_app(), procrastinate.App)


def test_the_worker_can_map_every_table_it_will_query() -> None:
    """A job that queries `attempts` must not fail on an unimported model.

    The worker imports `app/features/*/jobs.py` and nothing else, so a mapper
    whose foreign key names a table no imported module declares cannot be
    configured — `attempts.peer_session_id` → `practice_sessions` is one, and
    `attempts.set_entry_id` → `station_set_entries` another. The failure is
    order-dependent, which is worse than being reliable: it surfaced only when a
    circuit transition ran in a real worker, and marking was one import away
    from the same fate.

    In a **subprocess**, because that is the whole point. Every test in this
    suite runs in a process where `conftest` has already imported the app, so
    the bug is invisible from inside it — which is exactly why it reached a
    deployment.
    """
    import subprocess
    import sys

    probe = (
        "from app.worker.main import build_worker_app;"
        "from sqlalchemy.orm import configure_mappers;"
        "build_worker_app();"
        "configure_mappers();"
        "print('mapped')"
    )
    result = subprocess.run(  # noqa: S603 - our own interpreter, a literal probe
        [sys.executable, "-c", probe], capture_output=True, text=True, cwd=str(ROOT)
    )
    assert result.returncode == 0, result.stderr[-1500:]
    assert "mapped" in result.stdout
