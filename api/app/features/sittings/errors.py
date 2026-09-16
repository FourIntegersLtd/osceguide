from __future__ import annotations

from app.core.errors import Conflict, NotFound


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


# Binding a rubric is `stations`' rule, so its errors are this slice's
# vocabulary too. Re-exported rather than redefined: the previous local class
# was never raised, so the route advertised a code that could not happen while
# the invariant it named went unenforced.
from app.features.stations.errors import (  # noqa: E402
    TemplateNotPublishedError,
    TemplateVersionNotFound,
)

__all__ = ["TemplateNotPublishedError", "TemplateVersionNotFound"]


class CircuitNotStarted(Conflict):
    """No room yet, so there is nowhere to put an agent."""

    code = "circuit_not_started"
    default_message = "Start the circuit before dispatching an agent"
