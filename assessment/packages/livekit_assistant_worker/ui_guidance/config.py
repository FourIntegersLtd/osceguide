import os


def is_ui_guidance_enabled() -> bool:
    """Return True unless ENABLE_UI_GUIDANCE is set to a falsy value."""
    v = os.getenv("ENABLE_UI_GUIDANCE", "true").strip().lower()
    return v not in ("0", "false", "no", "off")

