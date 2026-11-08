"""What can go wrong scheduling, editing or running a sitting.

Each error carries the `code` a client branches on, never the message. A few
codes belong to other slices (rubrics, stations, voice) and are re-exported
here because this slice's routes are where a client actually meets them.
"""

from __future__ import annotations

from app.core.errors import Conflict, Forbidden, NotFound
from app.features.attempts.errors import MarkingNotReady
from app.features.roster.errors import CohortNotFound, TraineeNotOnRosterError, TraineeRevokedError


class SittingNotFound(NotFound):
    """No sitting exists with the given id, for this organisation."""

    code = "sitting_not_found"
    default_message = "No such sitting"


class CircuitNotFound(NotFound):
    """No circuit exists with the given id, for this organisation."""

    code = "circuit_not_found"
    default_message = "No such circuit"


class SlotNotFound(NotFound):
    """No slot exists with the given id, on this circuit."""

    code = "slot_not_found"
    default_message = "No such slot"


class InvalidCircuitError(Conflict):
    """The roster and stations sent do not describe a circuit the rules allow."""

    code = "invalid_circuit"
    default_message = "That circuit cannot be built as described"


class LeadCannotRun(Conflict):
    """The person named to lead a circuit holds no staff role that may run circuits."""

    code = "lead_cannot_run"
    default_message = "A circuit's lead must be an administrator or supervisor of this organisation"


class NotYourStation(Forbidden):
    """An assessor asked to hear a station that is assigned to somebody else."""

    code = "not_your_station"
    default_message = "This station is assigned to another assessor"


class JoinNotOpen(Conflict):
    """A staggered rotation cannot start before its own start time (less ten minutes)."""

    code = "join_not_open"
    default_message = "This circuit's start time has not come yet"


class CircuitLockedError(Conflict):
    """A structural edit was refused because a station is running or has feedback."""

    code = "circuit_locked"
    default_message = "A station is in progress or feedback exists; the circuit cannot be changed"


class CircuitAlreadyEndedError(Conflict):
    """An action needs a circuit that is still open, and this one has finished."""

    code = "circuit_already_ended"
    default_message = "That circuit has already finished"


class NotPermittedInModeError(Conflict):
    """An action was tried against the wrong kind of circuit (training or exam)."""

    code = "not_permitted_in_mode"
    default_message = "That action does not apply to this kind of circuit"


class SittingLockedError(Conflict):
    """An assessment-bearing change to a sitting that is already running.

    Its own code rather than `circuit_locked`, because the thing being refused
    is a change to the sitting — the rubric, the mode, the type — and the client
    says something different about it: not "someone is mid-station" but "people
    have been examined against this, so what it examines is fixed".
    """

    code = "sitting_locked"
    default_message = "This sitting has begun, so what it examines cannot be changed"


class TraineeAlreadyOnCircuitError(Conflict):
    """Somebody was about to be added to a circuit they are already rostered on."""

    code = "trainee_already_on_circuit"
    default_message = "That person is already on this circuit"


class StationNotOnCircuitError(Conflict):
    """A station was named that this circuit does not run."""

    code = "station_not_on_circuit"
    default_message = "That station is not on this circuit"


# Binding a rubric is `rubrics`' rule and binding a station is `stations`',
# so both slices' errors are this slice's vocabulary too. Re-exported rather
# than redefined: local classes here were previously never raised, so routes
# advertised codes that could not happen.
from app.features.catalog.errors import ProgrammeNotActive, ProgrammeNotFound  # noqa: E402
from app.features.rubrics.errors import (  # noqa: E402
    RubricVersionNotFound,
    RubricVersionNotPublished,
)
from app.features.stations.errors import TemplateNotPublishedError  # noqa: E402

# Putting a patient into a room is `voice`'s job, so its refusal is this
# slice's vocabulary too: every route that starts or resumes a station can
# answer with it.
from app.features.voice.errors import VoiceUnavailable  # noqa: E402

__all__ = [
    "CohortNotFound",
    "ExamRubricNotReady",
    "MarkingNotReady",
    "ProgrammeNotActive",
    "ProgrammeNotFound",
    "ProgrammeRequired",
    "RubricVersionNotFound",
    "RubricVersionNotPublished",
    "TemplateNotPublishedError",
    "TraineeNotOnRosterError",
    "TraineeRevokedError",
    "VoiceUnavailable",
]


class ProgrammeRequired(Conflict):
    """A sitting was created or edited without the programme its rubric comes from."""

    code = "programme_required"
    default_message = "A sitting must name the programme it is running"


class ExamRubricNotReady(Conflict):
    """The programme's exam has no published rubric version to mark against yet."""

    code = "exam_rubric_not_ready"
    default_message = "That programme's exam is not ready to mark against yet"


class CircuitNotStarted(Conflict):
    """No room yet, so there is nowhere to put an agent."""

    code = "circuit_not_started"
    default_message = "Start the circuit before dispatching an agent"


class CircuitNotLive(Conflict):
    """Not started, or already over. Nothing may be done to it and nobody may join."""

    code = "circuit_not_live"
    default_message = "That circuit is not running"


class CircuitPausedError(Conflict):
    """An action needs a running clock, and this circuit's is stopped."""

    code = "circuit_paused"
    default_message = "The clock is stopped; resume it first"


class CircuitNotPausedError(Conflict):
    """A resume was asked for on a circuit whose clock is already running."""

    code = "circuit_not_paused"
    default_message = "The clock is running; there is nothing to resume"


class NoActiveStation(Conflict):
    """Asked to act on the station in progress when there is not one.

    A circuit on a break has no station, which is the case this exists for:
    "send the patient in again" during a break would otherwise dispatch into a
    room where nobody is due.
    """

    code = "no_active_station"
    default_message = "No station is in progress"


class NotATrainingCircuit(Conflict):
    """Mic and floor controls, and closing a kept-open room, exist for training circuits only."""

    code = "not_a_training_circuit"
    default_message = "That only applies to a training circuit."


class CircuitNotEnded(Conflict):
    """The room can be closed once the circuit has ended, not while it runs."""

    code = "circuit_not_ended"
    default_message = "End the circuit before closing the room."


class SchemeNotShown(Forbidden):
    """A marking scheme is shown during a training station, to people who are not sitting it."""

    code = "scheme_not_shown"
    default_message = "The marking scheme is not shown for this station."


class PeerMarksNotAllowed(Forbidden):
    """Peer marks exist on a training circuit; an exam has none."""

    code = "peer_marks_not_allowed"
    default_message = "Marking another trainee is only part of practice circuits."


class PeerMarksOwnTurn(Forbidden):
    """The trainee being consulted does not mark their own turn."""

    code = "peer_marks_own_turn"
    default_message = "You cannot mark your own turn."


class PeerMarksClosed(Conflict):
    """The turn is not running, and its feedback has already been shared."""

    code = "peer_marks_closed"
    default_message = "This turn is no longer open for marks."


class PeerMarkRatingUnknown(Conflict):
    """A peer mark's rating is not one of the panel's Met / Partly / Not met."""

    code = "peer_mark_rating_unknown"
    default_message = "That rating is not one of Met, Partly or Not met."


class PeerMarkItemUnknown(Conflict):
    """A mark names something that is not in the station's marking scheme."""

    code = "peer_mark_item_unknown"
    default_message = "That item is not in this station's marking scheme."


class CandidateAlreadySat(Conflict):
    """Marking absent is for somebody who never started: they have a station under way or marked."""

    code = "candidate_already_sat"
    default_message = "This person has already started a station, so they cannot be marked absent."


class CandidateMarkedAbsent(Conflict):
    """The supervisor recorded this candidate as absent, so the room is closed to them."""

    code = "candidate_marked_absent"
    default_message = "You have been marked absent from this session."


class CandidateStillConnected(Conflict):
    """A re-join is for a connection that dropped; the patient is still talking to the candidate."""

    code = "candidate_still_connected"
    default_message = "The candidate is still connected, so there is nothing to re-join."


class RejoinAlreadyUsed(Conflict):
    """One re-join per station; a second is a decision for the Add time or Repeat station controls."""

    code = "rejoin_already_used"
    default_message = "A re-join has already been allowed for this station."


# What "you cannot do that to this circuit" can mean, as one tuple: every
# route that acts on a live examination declares the same three, and three
# spellings of one list is how a route ends up advertising a code it cannot
# raise.
LIVE_CIRCUIT_REFUSALS = (CircuitNotFound, CircuitNotLive)


class TemplateNotFound(NotFound):
    """No sitting template exists with the given id, for this organisation."""

    code = "template_not_found"
    default_message = "No such template"


class TemplateNameTaken(Conflict):
    """Another template of this organisation already has that name."""

    code = "template_name_taken"
    default_message = "A template with that name already exists"
