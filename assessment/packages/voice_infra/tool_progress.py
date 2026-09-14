"""Async-tool progress: a status line plus repeating filler speech until the tool finishes."""

from __future__ import annotations

from collections.abc import Callable

_FILLER_LINES: tuple[str, ...] = (
    "Still with you — one moment.",
    "Still working on that for you.",
    "Almost there — thanks for waiting.",
    "Hang on, I am still on it.",
)

FILLER_DELAY_SECONDS = 4.0
FILLER_INTERVAL_SECONDS = 10.0


def filler_line(step: int) -> str:
    """Rotating filler speech while a tool blocks (LiveKit ``with_filler`` source)."""
    return _FILLER_LINES[step % len(_FILLER_LINES)]


def filler_kwargs() -> dict[str, float | int | None | Callable[[int], str]]:
    """Repeat filler until the surrounding ``async with`` block ends."""
    return {"delay": FILLER_DELAY_SECONDS, "interval": FILLER_INTERVAL_SECONDS, "max_steps": None}
