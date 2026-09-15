"""
AnthropicComputerTool — Anthropic (Claude) vision backend.

Returns the captured screenshot as a native Anthropic image block so Claude
sees the page directly and returns pixel coordinates in the image space.

Image tool_result trick:
  Returning json.dumps([{"type": "image", "source": {"type": "base64", ...}}])
  makes Claude receive a real screenshot image in the tool result.
"""

import json

from livekit.agents import JobContext

from livekit_assistant_worker.ui_guidance.base_computer_toolset import BaseComputerTool
from livekit_assistant_worker.ui_guidance.navigation import NavigationModeState


class AnthropicComputerTool(BaseComputerTool):
    """
    Anthropic (Claude) vision: captures a screenshot, returns it as an image block
    so Claude sees the page directly, then uses show_pointer for overlay coordinates.
    """

    _LOG_PREFIX = "ANTHROPIC"

    async def _analyse_screenshot(self, jpeg_b64: str, media_type: str) -> str:
        return json.dumps([{
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": jpeg_b64,
            },
        }])


def build_anthropic_computer_tool(ctx: JobContext, worker_type: str, navigation: NavigationModeState | None = None):
    """Creates an AnthropicComputerTool and returns the function_tool-decorated callable."""
    return AnthropicComputerTool(ctx, worker_type, navigation).as_function_tool()
