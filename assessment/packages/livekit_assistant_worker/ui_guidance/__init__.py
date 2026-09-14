"""Voice-driven UI guidance: screenshot via chunked data channel, Claude vision, pointer overlay.

Ported from the legacy worker's ``ui_guidance`` package; the frontend
counterpart lives in ``frontend/src/shared/livekit-ui-guidance``.
"""

from livekit_assistant_worker.ui_guidance.anthropic_computer_toolset import build_anthropic_computer_tool
from livekit_assistant_worker.ui_guidance.config import is_ui_guidance_enabled
from livekit_assistant_worker.ui_guidance.navigation import NavigationModeState

__all__ = ["NavigationModeState", "build_anthropic_computer_tool", "is_ui_guidance_enabled"]
