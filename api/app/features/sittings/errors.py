from __future__ import annotations

from app.core.errors import Conflict, NotFound
from app.features.roster.errors import TraineeNotOnRosterError, TraineeRevokedError


class SittingNotFound(NotFound):
    code = "sitting_not_found"
    default_message = "No such sitting"


class CircuitNotFound(NotFound):
    code = "circuit_not_found"
    default_message = "No such circuit"


class SlotNotFound(NotFound):
    code = "slot_not_found"
    default_message = "No such slot"


class InvalidCircuitError(Conflict):
    code = "invalid_circuit"
    default_message = "That circuit cannot be built as described"


class CircuitLockedError(Conflict):
    code = "circuit_locked"
    default_message = "A station is in progress or feedback exists; the circuit cannot be changed"


class CircuitAlreadyEndedError(Conflict):
    code = "circuit_already_ended"
    default_message = "That circuit has already finished"


class NotPermittedInModeError(Conflict):
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
    code = "trainee_already_on_circuit"
    default_message = "That person is already on this circuit"


class StationNotOnCircuitError(Conflict):
    code = "station_not_on_circuit"
    default_message = "That station is not on this circuit"


# Binding a rubric is `rubrics`' rule and binding a station is `stations`',
# so both slices' errors are this slice's vocabulary too. Re-exported rather
# than redefined: local classes here were previously never raised, so routes
# advertised codes that could not happen.
from app.features.catalog.errors import ProgrammeNotFound  # noqa: E402
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
    "ExamRubricNotReady",
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
    code = "programme_required"
    default_message = "A sitting must name the programme it is running"


class ExamRubricNotReady(Conflict):
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
    code = "circuit_paused"
    default_message = "The clock is stopped; resume it first"


class CircuitNotPausedError(Conflict):
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
