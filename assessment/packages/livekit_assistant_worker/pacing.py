"""The clock an interaction runs against, when the backend sent one.

The model has no sense of elapsed time on its own, so left alone it paces by
turn count: it works through whatever list it was given and finishes early or
late by accident. This pushes the backend's marks into its context as they go
by, and offers a tool it can ask at any point.

Two things it deliberately does not do. It never ends the interaction --- the
last mark is a note like any other, and the session runs until the person
leaves. And it never makes the model speak: notes go in through
``apply_notice``, which the model reads before its next reply rather than
answering on the spot.

The worker knows nothing about what kind of interaction this is. It receives
seconds and finished sentences, and does arithmetic on them.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from voice_infra.notices import apply_notice

from .bootstrap import PacingPlan

logger = logging.getLogger(__name__)

__all__ = ["ConsultationClock"]


def _spoken_duration(seconds: float) -> str:
    """Said the way a person says it; this text reaches the model."""
    whole = max(0, int(round(seconds)))
    minutes, remainder = divmod(whole, 60)
    if not minutes:
        return f"{remainder} sec"
    if not remainder:
        return f"{minutes} min"
    return f"{minutes} min {remainder} sec"


class ConsultationClock:
    """Marks pushed into the model's context as they pass, plus what to tell the time tool.

    Built and started separately on purpose: the tool needs the object before
    the session opens, and time zero is the moment the interaction actually
    opens, not the moment the tool list was assembled.
    """

    def __init__(self, plan: PacingPlan) -> None:
        self._plan = plan
        self._started_at: float | None = None
        self._tasks: list[asyncio.Task] = []

    # -- lifecycle ----------------------------------------------------------------

    def start(self, agent: Any) -> None:
        """Begin timing and schedule every mark. Safe to call once."""
        if self._started_at is not None:
            return
        self._started_at = time.monotonic()
        for mark in self._plan.marks:
            self._tasks.append(asyncio.create_task(self._fire(agent, mark.at_seconds, mark.note)))

    async def cancel(self, *_args: Any) -> None:
        """Drop any mark that has not fired. Takes ignored args so it can be a shutdown callback."""
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def _fire(self, agent: Any, at_seconds: float, note: str) -> None:
        # Sleep against the elapsed total rather than accumulating per-mark sleeps,
        # so a slow note never pushes every later mark out behind it.
        try:
            delay = at_seconds - (self.elapsed() or 0.0)
            if delay > 0:
                await asyncio.sleep(delay)
            logger.info("[pacing] mark at %ss", at_seconds)
            await apply_notice(agent, note)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — a lost mark must not end the interaction
            logger.warning("[pacing] mark at %ss not applied: %s", at_seconds, exc)

    # -- what the tool reads ------------------------------------------------------

    def elapsed(self) -> float | None:
        return None if self._started_at is None else time.monotonic() - self._started_at

    def _phase_label(self, elapsed: float) -> tuple[str, float] | None:
        for phase in self._plan.phases:
            if elapsed < phase.until_seconds:
                return phase.label, phase.until_seconds
        return None

    def status_text(self) -> str:
        """Where things stand, in the words the model should think in."""
        elapsed = self.elapsed()
        if elapsed is None:
            return "This has not started yet."
        total = self._plan.total_seconds
        gone = _spoken_duration(elapsed)
        if elapsed >= total:
            return (
                f"About {gone} gone of {_spoken_duration(total)}. You are past the time set aside: "
                "finish the point you are on and close. Do not start anything new."
            )
        left = _spoken_duration(total - elapsed)
        phase = self._phase_label(elapsed)
        where = ""
        if phase is not None:
            label, until = phase
            where = f" You should be in: {label}, until about {_spoken_duration(until)}."
        return f"About {gone} gone of {_spoken_duration(total)}; about {left} left.{where}"
