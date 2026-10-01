"""The user's chosen navigation mode for on-screen guidance, owned per session.

``guide`` highlights controls and waits for the user; ``automate`` lets the
agent click. The browser announces the choice over the data channel; the
session records it here and the computer tool reads it before every click.
"""

from __future__ import annotations

from typing import Literal

NavigationMode = Literal["guide", "automate"]
NAVIGATION_MODES: tuple[NavigationMode, ...] = ("guide", "automate")
DEFAULT_NAVIGATION_MODE: NavigationMode = "guide"


class NavigationModeState:
    """Holds the navigation mode the user chose for one session."""

    def __init__(self, mode: NavigationMode = DEFAULT_NAVIGATION_MODE) -> None:
        self._mode: NavigationMode = mode

    @property
    def mode(self) -> NavigationMode:
        return self._mode

    def set(self, mode: str) -> bool:
        """Record a mode; unknown values are ignored and reported as ``False``."""
        if mode not in NAVIGATION_MODES:
            return False
        self._mode = mode  # type: ignore[assignment]
        return True
