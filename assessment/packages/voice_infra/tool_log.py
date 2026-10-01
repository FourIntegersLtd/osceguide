"""Structured logs for agent function tools; grep for the prefix in worker output."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger("voice_infra.tools")

AGENT_TOOL_PREFIX = "____----- [AGENT_TOOL]"


def agent_tool_log(message: str) -> None:
    logger.info("%s %s", AGENT_TOOL_PREFIX, message)


def log_llm_tool_use_shape(tool_name: str, raw_arguments: dict[str, Any], *, run_ctx: Any | None = None) -> None:
    """Log the invocation in an Anthropic-style tool_use shape for debugging."""
    call_id = "unknown"
    if run_ctx is not None:
        function_call = getattr(run_ctx, "function_call", None)
        if function_call is not None:
            call_id = getattr(function_call, "call_id", None) or getattr(function_call, "id", None) or "unknown"
    payload = {"type": "tool_use", "id": call_id, "name": tool_name, "input": dict(raw_arguments)}
    logger.info("%s llm_tool_use\n%s", AGENT_TOOL_PREFIX, json.dumps(payload, indent=2, default=str))
