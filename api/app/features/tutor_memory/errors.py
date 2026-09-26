"""The refusals a tutor memory route or worker call can return."""

from __future__ import annotations

from app.core.errors import InvalidInput, NotFound
from app.features.assistant.errors import SessionNotFound, SessionNotJoinable

# Re-exported so this slice's worker router documents what the session lookup
# can refuse without naming another slice. The same classes, not copies: the
# codes are the contract.
__all__ = [
    "NoteNotFound",
    "SessionNotFound",
    "SessionNotJoinable",
    "ToolArgumentsInvalid",
    "UnknownTool",
]


class UnknownTool(NotFound):
    """The model asked to call a tool that isn't in this session's catalogue."""

    code = "unknown_tool"
    default_message = "No such tool"


class ToolArgumentsInvalid(InvalidInput):
    """The model's tool call had arguments that fail `domain.validate_tool_arguments`."""

    code = "tool_arguments_invalid"
    default_message = "That tool was called with arguments it does not accept"


class NoteNotFound(NotFound):
    """The stated fact or session summary being looked up does not exist."""

    code = "tutor_note_not_found"
    default_message = "No such note"
