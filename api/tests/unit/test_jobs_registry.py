"""The worker runs the tasks the slices declare.

The one test that would have caught the worker starting with no tasks at all:
every job test called the task body directly, so `register()` going uncalled
was invisible. This asks the app itself.
"""

from __future__ import annotations

import procrastinate

from app.core import jobs

FEATURE_TASKS = {"score_attempt", "deliver_outbound_messages", "match_practice_queue"}
PERIODIC_TASKS = {"deliver_outbound_messages", "match_practice_queue"}


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
