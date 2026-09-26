"""SEC-008: a hard wall-clock cap ends a session that would otherwise run forever.

The pacing clock never ends an interaction and only the GPT-Live runtime carries
its own limit, so a pipeline session runs until the client disconnects. These
prove the backstop: the cap shuts the job down at the limit, a clean teardown
cancels it first so it never fires late, and it can be tuned or turned off.
"""

from __future__ import annotations

import asyncio

import pytest

from livekit_assistant_worker import session_cap as cap_module
from livekit_assistant_worker.session_cap import SessionCap, configured_seconds, register_session_cap

from _worker_fakes import FakeJobContext


def test_the_cap_shuts_the_job_down_once_the_limit_passes() -> None:
    async def scenario() -> FakeJobContext:
        ctx = FakeJobContext()
        cap = SessionCap(ctx, max_seconds=0.02)
        cap.start()
        await asyncio.sleep(0.05)
        return ctx

    ctx = asyncio.run(scenario())
    assert ctx.shutdowns == ["session_cap"], "the cap asks the job context to shut down"


def test_a_clean_teardown_cancels_the_cap_before_it_fires() -> None:
    async def scenario() -> FakeJobContext:
        ctx = FakeJobContext()
        cap = SessionCap(ctx, max_seconds=10.0)
        cap.start()
        # The session ended normally well inside the cap; cancel and wait longer
        # than the timer would have slept to prove it never fires.
        await cap.cancel()
        await asyncio.sleep(0.02)
        return ctx

    ctx = asyncio.run(scenario())
    assert ctx.shutdowns == [], "a session that ends on its own is never force-closed"


def test_register_starts_the_cap_and_wires_its_teardown() -> None:
    async def scenario() -> tuple[FakeJobContext, SessionCap | None]:
        ctx = FakeJobContext()
        cap = register_session_cap(ctx, max_seconds=0.02)
        return ctx, cap

    ctx, cap = asyncio.run(scenario())
    assert cap is not None
    assert cap.cancel in ctx.shutdown_callbacks, "the cap is torn down with the job"
    assert cap.elapsed() is not None, "and it starts counting immediately"


def test_a_non_positive_cap_is_disabled() -> None:
    async def scenario() -> tuple[FakeJobContext, SessionCap | None]:
        ctx = FakeJobContext()
        cap = register_session_cap(ctx, max_seconds=0)
        await asyncio.sleep(0.02)
        return ctx, cap

    ctx, cap = asyncio.run(scenario())
    assert cap is None, "zero turns the cap off — the pre-SEC-008 behaviour"
    assert ctx.shutdown_callbacks == [] and ctx.shutdowns == []


def test_the_cap_reads_its_length_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(cap_module.SESSION_CAP_ENV, "120")
    assert configured_seconds() == 120.0

    monkeypatch.setenv(cap_module.SESSION_CAP_ENV, "off")
    assert configured_seconds() <= 0, "'off' disables the cap"

    monkeypatch.delenv(cap_module.SESSION_CAP_ENV, raising=False)
    assert configured_seconds() == cap_module.MAX_SESSION_SECONDS, "unset falls back to the one-hour default"
