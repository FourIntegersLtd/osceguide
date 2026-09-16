from __future__ import annotations

from app.core.errors import Conflict, InvalidInput, NotFound


class SessionNotFound(NotFound):
    code = "assistant_session_not_found"
    default_message = "No such assistant session"


class UnknownAssistantTypeError(InvalidInput):
    code = "unknown_assistant_type"
    default_message = "No assistant handles that kind of session"


class SessionNotJoinable(Conflict):
    code = "assistant_session_not_joinable"
    default_message = "That session has already finished"


class SessionNotReady(Conflict):
    code = "assistant_session_not_ready"
    default_message = "That session has no rendered instructions"
