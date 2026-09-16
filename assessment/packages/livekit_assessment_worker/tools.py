"""Function tools an interaction profile may name, built from its rendered tool context.

The profile lists tool names; this module owns their implementations. A tool
only ever works with the transcript and the room, never with what the
transcript was about.

``highlight_lines``: the model refers to transcript lines by the short ids it
was shown in its instructions; the tool translates them through the
``id_mapping`` in the tool context and publishes the message ids, with the
model's recommendations, to the room so the client can highlight them.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Annotated, Any

from livekit.agents import RunContext
from livekit.agents.llm import function_tool
from pydantic import Field

logger = logging.getLogger(__name__)

HIGHLIGHT_LINES = "highlight_lines"
ID_MAPPING_KEY = "id_mapping"

ToolBuilder = Callable[[Any, dict[str, Any]], Any]


class UnknownToolError(ValueError):
    """The profile named a tool this worker does not implement."""


def highlight_payload(
    id_mapping: dict[str, str], line_ids: list[str] | None, recommendations: list[str]
) -> dict[str, Any]:
    ids = list(line_ids or [])
    translated = [id_mapping[line_id] for line_id in ids if id_mapping.get(line_id)]
    if len(translated) != len(ids):
        logger.warning("highlight_lines: %d of %d line ids not in the mapping", len(ids) - len(translated), len(ids))
    return {"transcript_message_ids": translated, "recommendations": list(recommendations)}


def build_highlight_lines_tool(ctx: Any, tool_context: dict[str, Any]):
    id_mapping = tool_context.get(ID_MAPPING_KEY)
    id_mapping = {str(k): str(v) for k, v in id_mapping.items()} if isinstance(id_mapping, dict) else {}
    if not id_mapping:
        logger.warning("highlight_lines enabled without an id mapping; every line id will be dropped")

    async def _highlight_lines(
        context: RunContext,
        recommendations: Annotated[list[str], Field(description="One or two short written takeaways to add to the panel")],
        line_ids: Annotated[
            list[str] | None,
            Field(description="Transcript line IDs this point refers to; omit when there is no transcript to anchor to"),
        ] = None,
    ) -> str:
        payload = highlight_payload(id_mapping, line_ids, recommendations)
        try:
            await ctx.room.local_participant.publish_data(json.dumps(payload).encode("utf-8"), reliable=True)
        except Exception as exc:  # noqa: BLE001 — the model must hear the tool failed
            logger.error("highlight_lines publish failed: %s", exc)
            return "Could not show the highlights on screen; describe the points verbally."
        return "Successfully sent feedback"

    return function_tool(
        _highlight_lines,
        name=HIGHLIGHT_LINES,
        description=(
            "Adds a point to the live insights panel the doctor is watching, and highlights the "
            "transcript lines it refers to. Call this as the debrief happens — once for each "
            "substantive point you make (a strength, something to change, something you agree to "
            "work on), not once at the end. Pass short written takeaways in `recommendations`; "
            "pass `line_ids` when a transcript moment anchors the point, and omit it when none does."
        ),
    )


TOOL_BUILDERS: dict[str, ToolBuilder] = {HIGHLIGHT_LINES: build_highlight_lines_tool}


def build_tools(ctx: Any, names: tuple[str, ...], tool_context: dict[str, Any]) -> list:
    """The tools a profile names, in order; an unknown name is a configuration error."""
    unknown = [name for name in names if name not in TOOL_BUILDERS]
    if unknown:
        raise UnknownToolError(f"profile names unknown tools {unknown}; available: {sorted(TOOL_BUILDERS)}")
    return [TOOL_BUILDERS[name](ctx, tool_context) for name in names]
