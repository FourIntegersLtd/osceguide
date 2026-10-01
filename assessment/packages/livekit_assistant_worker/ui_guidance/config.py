"""The on/off switch for on-screen guidance."""

import os


def is_ui_guidance_enabled() -> bool:
    """Return True unless ENABLE_UI_GUIDANCE is set to a falsy value."""
    value = os.getenv("ENABLE_UI_GUIDANCE", "true").strip().lower()
    return value not in ("0", "false", "no", "off")

