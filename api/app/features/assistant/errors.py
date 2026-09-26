from __future__ import annotations

from app.core.errors import Conflict, Forbidden, InvalidInput, NotFound
from app.features.voice.errors import VoiceUnavailable

# Re-exported so this slice's router documents it without naming another
# slice: the same class, because the code is the contract.
__all__ = [
    "SessionNotFound",
    "SessionNotJoinable",
    "SessionNotReady",
    "SessionNotYours",
    "UnknownAssistantTypeError",
    "VoiceUnavailable",
]


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


class SessionNotYours(Forbidden):

    code = "assistant_session_not_yours"
    default_message = "That assistant session belongs to somebody else"
