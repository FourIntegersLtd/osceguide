"""A sliding-window call budget for one guidance session.

Kept per instance rather than per process: a module-level bucket keyed by room
name is never evicted, so it grows for the life of the worker and carries one
job's spending into the next job that happens to share the interpreter.
"""

from __future__ import annotations

import os
import time

MAX_PER_MINUTE = int(os.getenv("UI_GUIDANCE_MAX_CALLS_PER_MINUTE", "30"))
WINDOW_SECONDS = 60.0


class RateLimit:
    def __init__(self, *, max_per_window: int = MAX_PER_MINUTE, window_seconds: float = WINDOW_SECONDS) -> None:
        self._max = max_per_window
        self._window = window_seconds
        self._calls: list[float] = []

    def take(self, *, now: float | None = None) -> bool:
        """Record a call and report whether it was allowed."""
        moment = time.monotonic() if now is None else now
        self._calls = [t for t in self._calls if moment - t < self._window]
        if len(self._calls) >= self._max:
            return False
        self._calls.append(moment)
        return True
