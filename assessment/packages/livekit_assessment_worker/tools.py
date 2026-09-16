"""Function tools an interaction profile may name, built from its rendered tool context.

The profile lists tool names; this module owns their implementations. A tool
only ever works with the transcript and the room, never with what the
transcript was about.

No tools are implemented at present. The seam stays because the profile
contract carries a ``tools`` tuple and the adapter switches the session into
async tool handling when one is named: a profile that names a tool this worker
does not implement is a configuration error, and says so rather than starting a
session whose model has been promised a tool that will never answer.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

ToolBuilder = Callable[[Any, dict[str, Any]], Any]


class UnknownToolError(ValueError):
    """The profile named a tool this worker does not implement."""


TOOL_BUILDERS: dict[str, ToolBuilder] = {}


def build_tools(ctx: Any, names: tuple[str, ...], tool_context: dict[str, Any]) -> list:
    """The tools a profile names, in order; an unknown name is a configuration error."""
    unknown = [name for name in names if name not in TOOL_BUILDERS]
    if unknown:
        raise UnknownToolError(f"profile names unknown tools {unknown}; available: {sorted(TOOL_BUILDERS)}")
    return [TOOL_BUILDERS[name](ctx, tool_context) for name in names]
