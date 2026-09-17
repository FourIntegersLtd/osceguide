"""Mirror of the frontend `src/shared/livekit-ui-guidance/contracts.ts` — keep in sync.

``tests/test_ui_guidance_contract_drift.py`` parses the TypeScript and fails when
the two sides disagree, so a rename here that is not made there is caught before
it reaches a room.
"""

# RPC method registered on the frontend; the worker calls this to trigger a screenshot.
# The frontend responds with chunk-count metadata; image data arrives via data-channel.
RPC_METHOD_SCREENSHOT_CHUNKED = "getScreenshotForGuidanceV2"

# RPC: worker asks the browser to perform a synthetic click at viewport CSS coordinates.
RPC_METHOD_PERFORM_CLICK = "performUiGuidanceClick"

# RPC: worker asks the browser to scroll the window or a nested scrollable container.
RPC_METHOD_SCROLL = "performUiGuidanceScroll"

# Browser → worker: one base64 fragment of a screenshot.
# Payload: type=sc_chunk, id=screenshotId, i=chunk_index, n=total_chunks, d=base64_fragment.
DATA_TYPE_SCREENSHOT_CHUNK = "sc_chunk"

# Browser → worker: the user chose guided highlights or hands-off navigation.
DATA_TYPE_NAV_MODE_CHOICE = "nav_mode_choice"

# Worker → browser: show the two-option navigation prompt.
DATA_TYPE_NAV_MODE_PROMPT = "nav_mode_prompt"

# Worker → browser: place or clear the pointer overlay.
POINTER_MESSAGE_TYPE = "pointer"

# Worker → browser: a guidance step started or finished.
# Payload: {"type": "guidance_progress", "schemaVersion": 2, "step": ..., "label": ...}
# The panel this drives is the only feedback that spans the vision turn, because
# the tool has already returned by the time the model starts looking at the image.
DATA_TYPE_GUIDANCE_PROGRESS = "guidance_progress"

# The steps a guidance turn moves through, in order. ``done`` clears the panel.
PROGRESS_STEP_CAPTURING = "capturing"
PROGRESS_STEP_READING = "reading"
PROGRESS_STEP_ACTING = "acting"
PROGRESS_STEP_DONE = "done"
PROGRESS_STEPS = (PROGRESS_STEP_CAPTURING, PROGRESS_STEP_READING, PROGRESS_STEP_ACTING, PROGRESS_STEP_DONE)

# Worker → browser: something the backend asked to show alongside a tool answer.
# The payload is the backend's, passed through unchanged; the worker never reads it.
DATA_TYPE_ASSISTANT_CARD = "assistant_card"

# Superseded by DATA_TYPE_GUIDANCE_PROGRESS; still published so a frontend from
# before the progress panel keeps its loading indicator. Remove one release on.
TOOL_RUNNING_MESSAGE_TYPE = "tool_running"

# Increment when a payload on this channel changes in a breaking way.
UI_GUIDANCE_SCHEMA_VERSION = 2
