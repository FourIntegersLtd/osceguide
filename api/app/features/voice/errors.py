from __future__ import annotations

from app.core.errors import AppError, Conflict
from app.features.attempts.errors import AttemptNotFound, AttemptNotYours

# Re-exported so the router documents these without reaching into another
# slice. The same classes, not copies: the codes are the contract.
__all__ = ["AttemptNotFound", "AttemptNotYours", "AttemptNotJoinable", "VoiceUnavailable"]


class VoiceUnavailable(AppError):
    status = 503
    code = "voice_unavailable"
    default_message = "The voice service is not available right now"


class AttemptNotJoinable(Conflict):
    code = "attempt_not_joinable"
    default_message = "That attempt has already finished"
