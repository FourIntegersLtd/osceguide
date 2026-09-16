"""Mapping the coordinates the model returns onto the browser's viewport.

The model sees an image of ``capture_width`` × ``capture_height`` and answers in
that space. The browser needs CSS pixels. Both the pointer overlay and the
synthetic click need the same conversion, which is why it lives here rather than
being written out twice at each call site.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_WIDTH = int(os.getenv("UI_GUIDANCE_DISPLAY_WIDTH", "1280"))
DEFAULT_HEIGHT = int(os.getenv("UI_GUIDANCE_DISPLAY_HEIGHT", "720"))


@dataclass(frozen=True)
class Viewport:
    """The last capture's dimensions, in both spaces."""

    viewport_width: int = DEFAULT_WIDTH
    viewport_height: int = DEFAULT_HEIGHT
    capture_width: int = DEFAULT_WIDTH
    capture_height: int = DEFAULT_HEIGHT

    @classmethod
    def from_metadata(cls, meta: dict) -> "Viewport":
        """Build from the screenshot RPC's metadata response."""
        return cls(
            viewport_width=int(meta["viewportWidth"]),
            viewport_height=int(meta["viewportHeight"]),
            capture_width=int(meta["captureWidth"]),
            capture_height=int(meta["captureHeight"]),
        )

    def to_viewport(self, x: float, y: float) -> tuple[int, int]:
        """Capture-space pixels to CSS viewport pixels, clamped to the visible area.

        A zero-sized capture would be a division by zero; it means the metadata was
        wrong, and scaling by 1 keeps the coordinate usable instead of failing the turn.
        """
        scale_x = self.viewport_width / self.capture_width if self.capture_width else 1.0
        scale_y = self.viewport_height / self.capture_height if self.capture_height else 1.0
        return (
            _clamp(round(x * scale_x), self.viewport_width),
            _clamp(round(y * scale_y), self.viewport_height),
        )


def _clamp(value: float, upper: int) -> int:
    return max(0, min(int(value), upper))
