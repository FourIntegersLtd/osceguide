"""Errors this slice's router can raise; each one's `code` is what callers branch on."""

from __future__ import annotations

from app.core.errors import AppError, Conflict
from app.features.attempts.errors import AttemptNotFound, AttemptNotYours

# Re-exported so the router documents these without reaching into another
# slice. The same classes, not copies: the codes are the contract.
__all__ = ["AttemptNotFound", "AttemptNotYours", "AttemptNotJoinable", "VoiceUnavailable"]


class VoiceUnavailable(AppError):
    """The voice service (LiveKit or the capacity store) could not be reached."""

    status = 503
    code = "voice_unavailable"
    default_message = "The voice service is not available right now"


class AttemptNotJoinable(Conflict):
    """The attempt is not in a status that can be joined right now."""

    code = "attempt_not_joinable"
    default_message = "That attempt has already finished"
