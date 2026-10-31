"""Voice-driven UI guidance: screenshot over the data channel, pointer overlay, synthetic clicks.

The frontend counterpart lives in ``frontend/src/shared/livekit-ui-guidance``;
``contracts.py`` mirrors its ``contracts.ts`` and a test fails when they drift.
"""

from livekit_assistant_worker.ui_guidance.agent import GuidanceAgent
from livekit_assistant_worker.ui_guidance.navigation import NavigationModeState
from livekit_assistant_worker.ui_guidance.pointer_tags import POINTER_TAG_SYNTAX, PointerTag
from livekit_assistant_worker.ui_guidance.progress import GuidanceProgress
from livekit_assistant_worker.ui_guidance.toolset import ComputerToolset, build_computer_toolset

__all__ = [
    "ComputerToolset",
    "GuidanceAgent",
    "GuidanceProgress",
    "NavigationModeState",
    "POINTER_TAG_SYNTAX",
    "PointerTag",
    "build_computer_toolset",
]
