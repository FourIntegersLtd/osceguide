"""Mirror of frontend `packages/livekit-ui-guidance/contracts.ts` — keep in sync."""

# RPC method registered on the frontend; backend calls this to trigger a screenshot.
# The frontend responds with chunk-count metadata; image data arrives via data-channel.
RPC_METHOD_SCREENSHOT_CHUNKED = "getScreenshotForGuidanceV2"

# Data-channel message type for individual screenshot chunks sent by the frontend.
# Payload shape (JSON): type=sc_chunk, id=screenshotId, i=chunk_index, n=total_chunks, d=base64_fragment.
DATA_TYPE_SCREENSHOT_CHUNK = "sc_chunk"

# Data-channel message type for pointer coordinates sent by the backend to the frontend.
POINTER_MESSAGE_TYPE = "pointer"

# Data-channel message type sent by the backend when a tool call starts/ends.
# Payload: {"type": "tool_running", "active": true|false}
# Used by the frontend to show a loading indicator during screenshot + vision analysis.
TOOL_RUNNING_MESSAGE_TYPE = "tool_running"

# Increment when the pointer payload schema changes in a breaking way.
UI_GUIDANCE_SCHEMA_VERSION = 1

# RPC: agent calls browser to perform a synthetic click at viewport CSS coordinates.
RPC_METHOD_PERFORM_CLICK = "performUiGuidanceClick"

# RPC: agent calls browser to scroll the window or nested scrollable containers.
RPC_METHOD_SCROLL = "performUiGuidanceScroll"

# Browser → agent: user chose guide vs hands-off (published by local participant).
DATA_TYPE_NAV_MODE_CHOICE = "nav_mode_choice"

# Agent → browser: show the two-option navigation prompt (optional; session buttons also exist).
DATA_TYPE_NAV_MODE_PROMPT = "nav_mode_prompt"
