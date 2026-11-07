"""Who may speak in a circuit's room. One rule, read by every token and every live change.

A training room is a video room for the group: everyone is seen, but only the person whose turn
it is and the supervisor are heard, unless the supervisor opens the floor. An exam room keeps its
old grants (the candidate speaks, the examiner only listens). Pure: no I/O.
"""

from __future__ import annotations

import uuid
from typing import Protocol

# The supervisor's LiveKit identity. Prefixed so it is legible in a participant list, and
# deliberately not `agent-*`: the sweep that clears stale patients matches on that prefix.
OBSERVER_PREFIX = "observer-"


class _Floor(Protocol):
    """Whatever carries the supervisor's open-floor switch: a circuit row."""

    open_floor: bool


def room_name_for(circuit_id: uuid.UUID) -> str:
    return f"circuit_{circuit_id}"


def mic_allowed(
    circuit: _Floor, active_trainee_id: uuid.UUID | None, identity: str, *, training: bool
) -> bool:
    """Whether `identity` may publish a microphone in this circuit's room."""
    is_supervisor = identity.startswith(OBSERVER_PREFIX)
    if not training:
        return not is_supervisor
    if is_supervisor or circuit.open_floor:
        return True
    return active_trainee_id is not None and identity == str(active_trainee_id)


def publish_sources(allowed: bool) -> list[str]:
    """A training participant's token sources: everyone has a camera, the microphone is the rule's."""
    return ["camera", "microphone"] if allowed else ["camera"]


def room_is_open(*, started: bool, ended: bool, has_room: bool, closed: bool, training: bool) -> bool:
    """Whether people may still join: a running circuit's room, or a training room kept after End."""
    if not started:
        return False
    if not ended:
        return has_room
    return training and not closed
