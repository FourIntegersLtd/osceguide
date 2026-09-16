"""Handing a screenshot to the session's own model.

There is no second model call here. Returning an image block as the tool result
makes the LiveKit Anthropic plugin place a real image inside the ``tool_result``,
so the vision work happens in the session model's next turn.
"""

from __future__ import annotations

import json


def as_image_block(image_b64: str, media_type: str) -> str:
    """The tool-result payload that puts the screenshot in front of the model."""
    return json.dumps([{
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": image_b64},
    }])


def as_text(text: str) -> str:
    """A plain-text tool result, in the same content-block shape."""
    return json.dumps([{"type": "text", "text": text}])
