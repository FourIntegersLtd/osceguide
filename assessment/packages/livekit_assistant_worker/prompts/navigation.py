"""What the model is told when the user picks a navigation mode on screen."""

from __future__ import annotations

NAVIGATION_MODE_PROMPTS: dict[str, str] = {
    "automate": (
        "[User selected Navigate for me (hands-off). You MUST use perform_click "
        "(never show_pointer) for every click step. Do NOT ask them to tap, click, "
        "or select — they are not touching the UI. After screenshot, perform_click, "
        "then screenshot to verify; continue steps without waiting for 'next'. "
        "Never use perform_click for destructive or submit actions.]"
    ),
    "guide": (
        "[User selected Guide me (highlights). Use only show_pointer; wait for "
        "them to say next between steps. Do not use perform_click.]"
    ),
}


def navigation_mode_prompt(mode: str) -> str:
    return NAVIGATION_MODE_PROMPTS[mode]
