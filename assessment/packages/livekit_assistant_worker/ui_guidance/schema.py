"""The ``computer`` tool as the model sees it.

This is prompt text, so it lives apart from the transport that carries out the
actions. What the model is told about the product — page names, navigation
labels, which control to look for — belongs in the instructions the backend
renders, never here.
"""

from __future__ import annotations

COMPUTER_TOOL_SCHEMA = {
    "name": "computer",
    "description": (
        "Look at, and act on, the application UI the user has open. "
        "Use action=screenshot to see the current page; the image comes back in the tool result. "
        "To point at something after a screenshot, write a pointer tag inline in your spoken "
        "reply — [POINT:x,y:Label] — rather than calling this tool again. The tag is removed "
        "before the words are spoken, so the highlight appears exactly as you name the control. "
        "Use action=perform_click only in hands-off mode, and action=scroll when the target is "
        "off-screen. action=show_pointer is a fallback for when you need a highlight without speaking."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["screenshot", "show_pointer", "perform_click", "scroll"],
                "description": (
                    "screenshot = capture the page as an image for you to read. "
                    "perform_click = synthetic click at coordinate (hands-off mode only). "
                    "scroll = scroll the viewport or a nested scrollable panel. "
                    "show_pointer = highlight at coordinate without speaking; prefer the inline "
                    "[POINT:x,y:Label] tag instead."
                ),
            },
            "coordinate": {
                "type": "array",
                "items": {"type": "number"},
                "description": (
                    "[x, y] in the pixel space of the most recent screenshot. "
                    "Required for show_pointer and perform_click."
                ),
            },
            "label": {
                "type": "string",
                "description": "The on-screen name of the element, exactly as the instructions name it.",
            },
            "direction": {
                "type": "string",
                "enum": ["up", "down", "left", "right"],
                "description": "Required for action=scroll.",
            },
            "amount_px": {
                "type": "number",
                "description": "Optional for action=scroll. Distance in CSS pixels; about 400 if omitted.",
            },
        },
        "required": ["action"],
    },
}
