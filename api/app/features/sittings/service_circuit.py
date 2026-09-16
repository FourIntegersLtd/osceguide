"""Running a circuit live: dispatching the agent, ending a consultation, and
whether the slots may still be rebuilt.

Split from `service.py` so scheduling a sitting and running one can each be
read on their own — they change for different reasons, and the running half is
the one a supervisor is holding a tablet in front of. Mirrors the split
`attempts` already makes between its candidate-facing and worker-facing sides.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ports import RoomAgents
from app.core.settings import Settings
from app.features.attempts import service as attempts
from app.features.sittings import domain, errors, repository
from app.features.sittings.reads import state as _state
from app.features.sittings.schemas import ConsultationEnded, DispatchResult, EditLock
from app.features.sittings.service import _raise, _require_circuit
from app.features.voice import service as voice

# Re-exported so the router wires the dependency without importing another
# slice: the service is this slice's public face, and the guard that enforces
# that is why routers stay one call deep.
get_room_agents = voice.get_room_agents


# `reviews` sits above this slice, so it cannot be imported here — but the
# edit lock needs to know whether any slot has been reviewed. Bound once by
# `main.py`, the same way `core.tenancy` binds its role policies.
_slot_has_review: list[Callable[[AsyncSession, uuid.UUID], Awaitable[bool]]] = []


def bind_feedback_lookup(lookup: Callable[[AsyncSession, uuid.UUID], Awaitable[bool]]) -> None:
    _slot_has_review.clear()
    _slot_has_review.append(lookup)


async def _any_slot_reviewed(session: AsyncSession, slot_ids: list[uuid.UUID]) -> bool:
    if not _slot_has_review:
        raise RuntimeError("No feedback lookup bound. app.main.create_app must call bind_feedback_lookup.")
    lookup = _slot_has_review[0]
    for slot_id in slot_ids:
        if await lookup(session, slot_id):
            return True
    return False


async def dispatch_agent(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit_id: uuid.UUID,
    *,
    slot_id: uuid.UUID,
    agents: RoomAgents,
    settings: Settings,
    now: datetime,
) -> DispatchResult:
    """Put an agent into the circuit's room for one slot (C5, C6).

    A supervisor's room is already up and the candidates are already in it, so
    unlike the consumer path there is no join to carry an implicit dispatch —
    the agent has to be put there explicitly.

    Each dispatch creates a new attempt. b2b reused the slot's single
    transcript column, so re-dispatching a station overwrote the first
    recording; here the previous attempt is failed and the new one sits beside
    it, and both recordings survive.
    """
    circuit = await _require_circuit(session, org_id, circuit_id, lock=True)
    try:
        domain.ensure_live(_state(circuit, has_feedback=False))
    except domain.CircuitAlreadyEnded as exc:
        _raise(exc)

    slot = await repository.slot_by_id(session, org_id, slot_id)
    if slot is None or slot.circuit_id != circuit_id:
        raise errors.SlotNotFound()
    room = circuit.room_name
    if not room:
        raise errors.CircuitNotStarted()

    attempt = await attempts.restart_for_slot(
        session,
        slot_id=slot.id,
        user_id=slot.trainee_id,
        org_id=org_id,
        station_version_id=slot.station_version_id,
        room_name=room,
        now=now,
    )

    agent_name, removed_before = await voice.dispatch_agent_into_room(
        agents=agents,
        settings=settings,
        room=room,
        attempt_id=attempt.id,
        candidate_ref=slot.trainee_id,
    )

    await repository.update_circuit(
        session, org_id, circuit_id, active_slot_id=slot.id, agent_dispatched_at=now
    )
    return DispatchResult(
        room_name=room,
        slot_id=slot.id,
        attempt_id=attempt.id,
        agent_name=agent_name,
        stale_agents_removed=removed_before,
    )


async def end_consultation(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit_id: uuid.UUID,
    *,
    agents: RoomAgents,
) -> ConsultationEnded:
    """Stop the current station without ending the circuit.

    The room stays up and the candidates stay in it; only the agent leaves, so
    the supervisor can debrief or move on to the next turn.
    """
    circuit = await _require_circuit(session, org_id, circuit_id, lock=True)
    removed = 0
    if circuit.room_name:
        removed = await voice.clear_agents_from_room(agents=agents, room=circuit.room_name)

    await repository.update_circuit(
        session, org_id, circuit_id, active_slot_id=None, agent_dispatched_at=None
    )
    return ConsultationEnded(circuit_id=circuit_id, agents_removed=removed, ended_at=circuit.ended_at)


async def read_edit_lock(session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID) -> EditLock:
    """Whether the circuit's slots may still be rebuilt, and why not (C3)."""
    circuit = await _require_circuit(session, org_id, circuit_id)
    slots = await repository.slots_for_circuit(session, org_id, circuit.id)
    has_feedback = await _any_slot_reviewed(session, [slot.id for slot in slots])

    reason = domain.edit_block(_state(circuit, has_feedback=has_feedback))
    return EditLock(circuit_id=circuit_id, editable=reason is None, reason=reason)
