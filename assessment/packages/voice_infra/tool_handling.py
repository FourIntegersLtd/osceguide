"""How an AgentSession narrates background tool progress, shared by every worker.

The template wraps every ``ctx.update`` before the model sees it. A tool with a
phase worth distinguishing passes its own ``template=`` per call; this is the
default for the rest.
"""

from __future__ import annotations

ASYNC_TOOL_HANDLING = {
    "async_options": {
        "update_template": (
            "Background tool `{function_name}` reports: {message}. "
            "Acknowledge briefly in plain speech, without implying the work has finished. "
            "Do not use markdown."
        ),
    },
}
