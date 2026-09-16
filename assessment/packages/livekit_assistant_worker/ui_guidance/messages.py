"""Every string the computer tool hands back to the model, in one place.

These are tool results, not product copy: they tell the model what happened and
what to do next. Keeping them together is what lets the action modules stay pure
transport, and makes it obvious when two failures are being described the same way.
"""

from __future__ import annotations

# Guardrails
RATE_LIMITED = "Rate limit reached; describe the remaining steps verbally instead."
NO_BROWSER = "The user's browser is not connected; continue with spoken guidance."
COORDINATE_REQUIRED = "This action needs coordinate=[x, y] from the most recent screenshot."
UNSUPPORTED_ACTION = "Action {action!r} is not supported. Use screenshot, show_pointer, perform_click or scroll."

# Screenshot
SCREENSHOT_FAILED = "Could not capture the screen; describe the steps verbally."

# Pointer
POINTER_PLACED = "Pointer placed on {label} at ({x}, {y})."
POINTER_FAILED = "Could not show the pointer; describe the steps verbally."

# Click
CLICK_NEEDS_AUTOMATE = (
    "perform_click is only available once the user has chosen hands-off navigation on screen. "
    "Point at the control instead and wait for them to say next."
)
CLICK_OK = "Clicked {label} at ({x}, {y})."
CLICK_OK_NAVIGATED = "Clicked {label} at ({x}, {y}). The page is now {path}."
CLICK_REJECTED = "The click did not land ({error}). Describe the next step verbally, or point at it instead."
CLICK_FAILED = "Could not perform the click; continue with spoken guidance."

# Scroll
SCROLL_NEEDS_DIRECTION = "scroll needs direction: up, down, left or right."
SCROLL_MOVED = "Scrolled {direction}. Take another screenshot to see whether the target is now visible."
SCROLL_STUCK = (
    "Scrolled {direction} but nothing moved; the page may use a different scroll container. "
    "Ask the user to scroll manually."
)
SCROLL_REJECTED = "The scroll did not run ({error}). Ask the user to scroll manually if needed."
SCROLL_FAILED = "Could not scroll the page; ask the user to scroll manually."
