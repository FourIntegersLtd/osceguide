"""Whether a circuit's slots may still be rebuilt.

One question, asked from two places: the structural edit that enforces it and
the console that needs to know before it offers one. It lives apart from the
rest of the slice because answering it means reaching into `reviews`, which
sits above this slice and so has to be bound in rather than imported.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.sittings import domain, repository
from app.features.sittings.reads import state as _state
from app.features.sittings.schemas import EditLock
from app.features.sittings.service import _require_circuit

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


async def read_edit_lock(session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID) -> EditLock:
    """Whether the circuit's slots may still be rebuilt, and why not (C3)."""
    circuit = await _require_circuit(session, org_id, circuit_id)
    slots = await repository.slots_for_circuit(session, org_id, circuit.id)
    has_feedback = await _any_slot_reviewed(session, [slot.id for slot in slots])

    reason = domain.edit_block(_state(circuit, has_feedback=has_feedback))
    return EditLock(circuit_id=circuit_id, editable=reason is None, reason=reason)
