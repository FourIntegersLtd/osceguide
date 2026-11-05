"""Which queues a worker process takes jobs from (WORKER_QUEUES, WORKER_EXCLUDE_QUEUES)."""

from __future__ import annotations

from app.core.settings import Settings
from app.worker.main import build_worker_app, worker_queues


def test_excluding_scoring_leaves_the_circuit_bell_and_nothing_of_scoring() -> None:
    app = build_worker_app()
    every = worker_queues(app, Settings(worker_exclude_queues=""))
    assert "scoring" in every
    queues = worker_queues(app, Settings(worker_exclude_queues="scoring"))
    assert "scoring" not in queues
    assert "circuits" in queues
    assert queues == sorted(set(every) - {"scoring"})


def test_naming_queues_takes_exactly_those() -> None:
    app = build_worker_app()
    settings = Settings(worker_queues=" scoring , health ", worker_exclude_queues="health")
    assert worker_queues(app, settings) == ["health", "scoring"]
