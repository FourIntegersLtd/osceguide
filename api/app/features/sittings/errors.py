"""What can go wrong scheduling, editing or running a sitting.

Each error carries the `code` a client branches on, never the message. A few
codes belong to other slices (rubrics, stations, voice) and are re-exported
here because this slice's routes are where a client actually meets them.
"""

from __future__ import annotations

from app.core.errors import Conflict, NotFound
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


# What "you cannot do that to this circuit" can mean, as one tuple: every
# route that acts on a live examination declares the same three, and three
# spellings of one list is how a route ends up advertising a code it cannot
# raise.
LIVE_CIRCUIT_REFUSALS = (CircuitNotFound, CircuitNotLive)
