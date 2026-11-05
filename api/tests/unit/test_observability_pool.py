"""Pool exhaustion is findable in Sentry and visible in the console's health report."""

from __future__ import annotations

import sys
import types

from sqlalchemy.exc import TimeoutError as PoolTimeout
from sqlalchemy.ext.asyncio import create_async_engine

from app.core import observability
from app.core.settings import Settings
from app.features.health import service


def test_a_pool_timeout_report_is_tagged() -> None:
    hint = {"exc_info": (PoolTimeout, PoolTimeout("QueuePool limit reached"), None)}
    assert observability.tag_pool_exhaustion({}, hint)["tags"] == {"db.pool_exhausted": "true"}


def test_other_errors_are_left_untagged() -> None:
    hint = {"exc_info": (ValueError, ValueError("x"), None)}
    assert observability.tag_pool_exhaustion({"tags": {"a": "b"}}, hint) == {"tags": {"a": "b"}}
    assert observability.tag_pool_exhaustion({}, {}) == {}


def test_sentry_uses_the_configured_trace_rate(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    seen: dict[str, object] = {}
    fake = types.SimpleNamespace(init=lambda **kwargs: seen.update(kwargs))
    monkeypatch.setitem(sys.modules, "sentry_sdk", fake)
    settings = Settings(sentry_dsn="https://k@example.invalid/1", sentry_traces_sample_rate=0.25)
    assert observability.configure_sentry(settings) is True
    assert seen["traces_sample_rate"] == 0.25
    assert seen["before_send"] is observability.tag_pool_exhaustion


def test_the_health_report_counts_the_pool(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    engine = create_async_engine("postgresql+psycopg://u:p@localhost/none", pool_size=10, max_overflow=4)
    monkeypatch.setattr(service, "get_engine", lambda: engine)
    monkeypatch.setattr(service, "get_settings", lambda: Settings(database_max_overflow=4))
    read = service.database_pool()
    assert read is not None
    assert (read.checked_out, read.overflow, read.ceiling) == (0, 0, 14)
