"""Errors this slice's router can raise; each one's `code` is what callers branch on."""

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
    """No assistant session exists with the given id."""

    code = "assistant_session_not_found"
    default_message = "No such assistant session"


class UnknownAssistantTypeError(InvalidInput):
    """The session names a `session_type` no worker recognises."""

    code = "unknown_assistant_type"
    default_message = "No assistant handles that kind of session"


class SessionNotJoinable(Conflict):
    """The session is not in a status that can be joined right now."""

    code = "assistant_session_not_joinable"
    default_message = "That session has already finished"


class SessionNotReady(Conflict):
    """The session has no rendered instructions for a worker to dispatch."""

    code = "assistant_session_not_ready"
    default_message = "That session has no rendered instructions"


class SessionNotYours(Forbidden):
    """The caller is not the user this assistant session belongs to."""

    code = "assistant_session_not_yours"
    default_message = "That assistant session belongs to somebody else"
