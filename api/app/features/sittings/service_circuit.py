"""Whether a circuit's slots may still be rebuilt.

One question, asked from two places: the structural edit that enforces it and
the console that needs to know before it offers one. A circuit is locked once
any of its slots has been reviewed.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.reviews import service as reviews
from app.features.sittings import domain, repository
from app.features.sittings.reads import state as _state
from app.features.sittings.schemas import EditLock
from app.features.sittings.service import _require_circuit


async def _any_slot_reviewed(session: AsyncSession, slot_ids: list[uuid.UUID]) -> bool:
    for slot_id in slot_ids:
        if await reviews.slot_has_review(session, slot_id):
            return True
    return False


async def read_edit_lock(session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID) -> EditLock:
    """Whether the circuit's slots may still be rebuilt, and why not (C3)."""
    circuit = await _require_circuit(session, org_id, circuit_id)
    slots = await repository.slots_for_circuit(session, org_id, circuit.id)
    has_feedback = await _any_slot_reviewed(session, [slot.id for slot in slots])

    reason = domain.edit_block(_state(circuit, has_feedback=has_feedback))
    return EditLock(circuit_id=circuit_id, editable=reason is None, reason=reason)
