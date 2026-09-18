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
    code = "unknown_tool"
    default_message = "No such tool"


class ToolArgumentsInvalid(InvalidInput):
    code = "tool_arguments_invalid"
    default_message = "That tool was called with arguments it does not accept"


class NoteNotFound(NotFound):
    code = "tutor_note_not_found"
    default_message = "No such note"
