"""Keeping a slow tool from sounding like a dropped call.

A filler only fires once the session has been idle for ``delay`` seconds with
nothing speaking or thinking, and every ``ctx.update`` restarts that dwell. A
delay longer than the tool it covers therefore never fires at all, which is why
these numbers are short: the wait they exist for is a few seconds, not a minute.
"""

from __future__ import annotations

from collections.abc import Callable

_FILLER_LINES: tuple[str, ...] = (
    "Still with you — one moment.",
    "Still working on that.",
    "Almost there, thanks for waiting.",
)

# Long enough that a tool finishing normally stays silent, short enough to land
# inside the wait rather than after it.
FILLER_DELAY_SECONDS = 1.2
FILLER_INTERVAL_SECONDS = 4.5

# A tool still running after three fillers is stuck; saying so a fourth time
# does not help, and the panel is still on screen.
FILLER_MAX_STEPS = 3

IN_PROGRESS_TEMPLATE = (
    "Background tool `{function_name}` is still running and reports: {message}. "
    "Say one short line in plain speech that keeps the user with you. "
    "Never imply the work has finished. Do not use markdown."
)


def filler_line(step: int) -> str:
    """Rotating filler speech while a tool blocks (LiveKit ``with_filler`` source)."""
    return _FILLER_LINES[step % len(_FILLER_LINES)]


def filler_kwargs() -> dict[str, float | int | None | Callable[[int], str]]:
    return {
        "delay": FILLER_DELAY_SECONDS,
        "interval": FILLER_INTERVAL_SECONDS,
        "max_steps": FILLER_MAX_STEPS,
    }
