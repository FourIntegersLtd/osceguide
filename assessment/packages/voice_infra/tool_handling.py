"""How an AgentSession narrates background tool progress, shared by every worker."""

from __future__ import annotations

ASYNC_TOOL_HANDLING = {
    "async_options": {
        "update_template": (
            "Background tool `{function_name}` reports: {message}. "
            "Acknowledge briefly in plain speech. Do not use markdown."
        ),
    },
}
