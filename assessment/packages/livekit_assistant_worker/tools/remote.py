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
import time
import uuid
from collections.abc import Awaitable, Callable, Iterable
from typing import Any

from livekit.agents import RunContext
from livekit.agents.llm import function_tool
from voice_infra import BackendEndpoints
from voice_infra.backend_http import sync_post_json_url

from livekit_assistant_worker.bootstrap import RemoteTool

logger = logging.getLogger(__name__)

REMOTE_TOOL_TIMEOUT_S = 8.0
# Past this, the model has already said its holding line and the pause is being
# heard. Logged rather than enforced: the timeout above is the enforcement, and
# what this wants to catch is the call that is slow but still answers.
SLOW_TOOL_MS = 1500
# Generic on purpose: the worker does not know what the tool was for.
TOOL_UNAVAILABLE = "That lookup is not available right now. Say so in one short sentence and carry on without it."

Publish = Callable[[dict[str, Any]], Awaitable[bool]]


def build_remote_tools(endpoints: BackendEndpoints, session_id: str, specs: Iterable[RemoteTool], *, publish: Publish) -> list:
    """One registered tool per spec, in the order the backend listed them."""
    return [_build(endpoints, session_id, spec, publish) for spec in specs]


def _build(endpoints: BackendEndpoints, session_id: str, spec: RemoteTool, publish: Publish):
    tool_url = endpoints.assistant_tool_url(session_id, spec.name)

    async def _impl(raw_arguments: dict[str, Any], context: RunContext) -> str:  # noqa: ARG001 — injected by the runtime
        return await call_backend_tool(endpoints, tool_url, spec.name, raw_arguments, publish)

    return function_tool(_impl, raw_schema={"name": spec.name, "description": spec.description, "parameters": spec.parameters})


async def call_backend_tool(
    endpoints: BackendEndpoints, tool_url: str, name: str, arguments: dict[str, Any] | None, publish: Publish
) -> str:
    """Forward one call; whatever goes wrong, the model gets a line it can say."""
    payload = {"tool": name, "arguments": arguments or {}, "call_id": uuid.uuid4().hex[:12]}
    # Timed on this side as well as the backend's, because the two measure
    # different things and only the difference explains a slow turn: the route
    # logs how long it took to answer, and this logs how long the model waited.
    started = time.monotonic()
    try:
        result = await asyncio.to_thread(
            sync_post_json_url,
            tool_url,
            payload,
            headers=endpoints.secret_headers(),
            timeout=REMOTE_TOOL_TIMEOUT_S,
            log_prefix="assistant_tool",
        )
    except Exception as exc:  # noqa: BLE001 — a failed lookup must not end the turn
        logger.warning("[assistant_tool] %s failed after %d ms: %s", name, _elapsed_ms(started), exc)
        return TOOL_UNAVAILABLE
    _log_round_trip(name, started)
    data = result.data if result.ok and isinstance(result.data, dict) else None
    text = data.get("result") if data else None
    if not isinstance(text, str) or not text.strip():
        logger.warning("[assistant_tool] %s answered HTTP %s without a result", name, result.status)
        return TOOL_UNAVAILABLE
    display = data.get("display")
    if isinstance(display, dict) and display.get("type"):
        await publish(display)
    return text


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def _log_round_trip(name: str, started: float) -> None:
    """One line per call, louder when it was slow enough to hear.

    A tool call sits inside a voice loop: the model says a holding line and
    then waits, so a slow tool is heard as a pause in the conversation rather
    than seen as a slow request. Nothing else in the system would show it.
    """
    elapsed = _elapsed_ms(started)
    if elapsed >= SLOW_TOOL_MS:
        logger.warning("[assistant_tool] %s answered in %d ms", name, elapsed)
    else:
        logger.info("[assistant_tool] %s answered in %d ms", name, elapsed)
