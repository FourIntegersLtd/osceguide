"""Tools the backend defines and answers: the worker registers a schema and forwards every call.

The worker holds no idea of what a tool means. The bootstrap names each one
with a description and a JSON schema for its arguments; when the model calls
it, the arguments go to the backend that dispatched the session and the text
that comes back is what the model reads. If the backend also returns
something to show, it is published on the data channel unchanged.

No ``context.update`` filler, for the reason ``check_time`` gives: a call is
one HTTP round-trip, and announcing it would defer the sentence the user is
waiting for.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable, Iterable
from typing import Any

from livekit.agents import RunContext
from livekit.agents.llm import function_tool
from voice_infra import BackendEndpoints
from voice_infra.backend_http import sync_post_json

from livekit_assistant_worker.bootstrap import RemoteTool
from livekit_assistant_worker.metadata import TOOL_PATH_TEMPLATE

logger = logging.getLogger(__name__)

REMOTE_TOOL_TIMEOUT_S = 8.0
# Generic on purpose: the worker does not know what the tool was for.
TOOL_UNAVAILABLE = "That lookup is not available right now. Say so in one short sentence and carry on without it."

Publish = Callable[[dict[str, Any]], Awaitable[bool]]


def build_remote_tools(endpoints: BackendEndpoints, session_id: str, specs: Iterable[RemoteTool], *, publish: Publish) -> list:
    """One registered tool per spec, in the order the backend listed them."""
    return [_build(endpoints, session_id, spec, publish) for spec in specs]


def _build(endpoints: BackendEndpoints, session_id: str, spec: RemoteTool, publish: Publish):
    path = TOOL_PATH_TEMPLATE.format(session_id=session_id, tool_name=spec.name)

    async def _impl(raw_arguments: dict[str, Any], context: RunContext) -> str:  # noqa: ARG001 — injected by the runtime
        return await call_backend_tool(endpoints, path, spec.name, raw_arguments, publish)

    return function_tool(_impl, raw_schema={"name": spec.name, "description": spec.description, "parameters": spec.parameters})


async def call_backend_tool(endpoints: BackendEndpoints, path: str, name: str, arguments: dict[str, Any] | None, publish: Publish) -> str:
    """Forward one call; whatever goes wrong, the model gets a line it can say."""
    payload = {"tool": name, "arguments": arguments or {}, "call_id": uuid.uuid4().hex[:12]}
    try:
        result = await asyncio.to_thread(
            sync_post_json, endpoints.required_base_url(), path, payload,
            headers=endpoints.secret_headers(), timeout=REMOTE_TOOL_TIMEOUT_S, log_prefix="assistant_tool",
        )
    except Exception as exc:  # noqa: BLE001 — a failed lookup must not end the turn
        logger.warning("[assistant_tool] %s failed: %s", name, exc)
        return TOOL_UNAVAILABLE
    data = result.data if result.ok and isinstance(result.data, dict) else None
    text = data.get("result") if data else None
    if not isinstance(text, str) or not text.strip():
        logger.warning("[assistant_tool] %s answered HTTP %s without a result", name, result.status)
        return TOOL_UNAVAILABLE
    display = data.get("display")
    if isinstance(display, dict) and display.get("type"):
        await publish(display)
    return text
