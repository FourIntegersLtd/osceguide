"""SEC-008: a hard wall-clock cap on how long a voice session may run.

The pacing clock never ends an interaction --- its last mark is a note like any
other, and the session runs until the person leaves. Only the GPT-Live runtime
carries a session policy of its own (see ``gpt_live_policy``). Left uncapped, a
pipeline session runs until the client disconnects, so a caller who simply stays
on the line drives unbounded LLM, speech-to-text and text-to-speech spend.

This closes that gap for every runtime: one wall-clock timer, and when it fires
the job is shut down. It is a resource guard and nothing else --- it holds no
view of what kind of interaction this is, never scores, and never reads or
changes any content. It counts seconds and, at the limit, asks the job context
to shut down.

The default matches the voice access token's own one-hour lifetime: past that a
session is almost certainly abandoned or abusive, and every second of it is
spend. Set ``ASSISTANT_MAX_SESSION_SECONDS`` to tune it; ``0`` or ``off``
disables the cap (the pre-SEC-008 behaviour, for a deployment that bounds spend
another way).
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["SESSION_CAP_ENV", "MAX_SESSION_SECONDS", "SessionCap", "register_session_cap"]

SESSION_CAP_ENV = "ASSISTANT_MAX_SESSION_SECONDS"
# One hour: the same bound the voice access token already carries.
MAX_SESSION_SECONDS = 3600.0
_DISABLE_WORDS = {"0", "off", "false", "no", "disabled", "none"}


def configured_seconds() -> float:
    """The cap in seconds from the environment; ``<= 0`` means disabled.

    Unset falls back to the one-hour default. ``0`` or a disable word (``off``,
    ``disabled`` …) returns ``0.0``, which turns the cap off. Anything else that
    will not parse as a number also falls back to the default rather than
    silently uncapping the session.
    """
    raw = (os.getenv(SESSION_CAP_ENV) or "").strip().lower()
    if not raw:
        return MAX_SESSION_SECONDS
    if raw in _DISABLE_WORDS:
        return 0.0
    try:
        return float(raw)
    except ValueError:
        logger.warning("[session_cap] %s=%r is not a number; using the default", SESSION_CAP_ENV, raw)
        return MAX_SESSION_SECONDS


class SessionCap:
    """A single wall-clock timer that shuts the job down once the limit passes."""

    def __init__(self, ctx: Any, *, max_seconds: float) -> None:
        self._ctx = ctx
        self._max_seconds = max_seconds
        self._task: asyncio.Task[None] | None = None
        self._started_at: float | None = None

    def start(self) -> None:
        """Begin the countdown. Safe to call once; a non-positive cap is a no-op."""
        if self._task is not None or self._max_seconds <= 0:
            return
        self._started_at = time.monotonic()
        self._task = asyncio.create_task(self._run())

    def elapsed(self) -> float | None:
        return None if self._started_at is None else time.monotonic() - self._started_at

    async def _run(self) -> None:
        try:
            await asyncio.sleep(self._max_seconds)
        except asyncio.CancelledError:
            raise
        logger.warning("[session_cap] session hit the %ss cap; shutting the job down", self._max_seconds)
        try:
            self._ctx.shutdown(reason="session_cap")
        except Exception as exc:  # noqa: BLE001 — a failed shutdown must not escape a bare task
            logger.warning("[session_cap] shutdown failed: %s", exc)

    async def cancel(self, *_args: Any) -> None:
        """Drop the timer. Takes ignored args so it can be a shutdown callback."""
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None


def register_session_cap(ctx: Any, *, max_seconds: float | None = None) -> SessionCap | None:
    """Install, start and wire teardown for the cap; ``None`` when it is disabled."""
    seconds = configured_seconds() if max_seconds is None else max_seconds
    if seconds <= 0:
        logger.info("[session_cap] disabled (%s <= 0)", SESSION_CAP_ENV)
        return None
    cap = SessionCap(ctx, max_seconds=seconds)
    cap.start()
    ctx.add_shutdown_callback(cap.cancel)
    return cap
