"""The refusals a peer-practice route can return. Clients branch on each one's `code`."""

from __future__ import annotations

from app.core.errors import Conflict, NotFound


class QueueEntryNotFound(NotFound):
    """This queue place is not this caller's, or has already gone."""

    code = "queue_entry_not_found"
    default_message = "You are not in the queue"


class SessionNotFound(NotFound):
    """No such practice session, or the caller was not one of its pair."""

    code = "practice_session_not_found"
    default_message = "No such practice session"


class AlreadyQueued(Conflict):
    """Joining twice keeps the place you already have.

    409 with the existing entry rather than a second place in the line.
    """

    code = "already_queued"
    default_message = "You are already waiting"


class SessionAlreadyEnded(Conflict):
    """The session this call would act on has already finished."""

    code = "practice_session_ended"
    default_message = "That session has already finished"


class NotYetAcceptedError(Conflict):
    """The pairing has not been accepted by both sides yet, so there is nowhere to join.

    Raised on presence while a session is still `pending_accept`: the room the
    handshake leads to does not exist for either side until then.
    """

    code = "practice_session_not_accepted"
    default_message = "Both sides must accept this match before joining it"


class FeedbackNotOpenError(Conflict):
    """Feedback is only taken on a session that ended after its consultation began."""

    code = "practice_feedback_not_open"
    default_message = "Feedback opens once a session you took part in has finished"


class NoStationsForExam(Conflict):
    """The exam has no published library station, so a pairing would have nothing to practise."""

    code = "no_stations_for_exam"
    default_message = "There are no stations to practise for that exam yet"


class PartnerUnavailableError(Conflict):
    """The other side of the accept handshake is no longer there.

    Raised when a caller tries to accept or decline a pairing that has
    already ended because the other person declined it or the 120-second
    accept window ran out before both sides answered.
    """

    code = "partner_unavailable"
    default_message = "Your partner is no longer available for this session"


class UnknownExamError(NotFound):
    """Mirrors `catalog.errors.UnknownExamError` and shares its code, so this
    slice's routes can document the refusal without importing another
    slice's error class into their signatures.
    """

    code = "unknown_exam"
    default_message = "No such exam"


# Re-exported, not copied: the code is the contract, and the slice named owns
# it. Queueing for a peer session runs the same entitlement check starting an
# attempt does, so `not_entitled` is part of this slice's vocabulary.
from app.features.entitlements.errors import NotEntitled  # noqa: E402
from app.features.voice.errors import VoiceUnavailable  # noqa: E402

__all__ = [
    "AlreadyQueued",
    "NotEntitled",
    "NotYetAcceptedError",
    "PartnerUnavailableError",
    "QueueEntryNotFound",
    "SessionAlreadyEnded",
    "SessionNotFound",
    "UnknownExamError",
    "VoiceUnavailable",
]
