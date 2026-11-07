"""Peer marks: a trainee watching another trainee's turn marks the same scheme.

Only on a training circuit, only by a trainee rostered on it who is not the one being consulted, and
only while that turn runs or until its feedback has been shared. The supervisor reads every marker's
marks live; the consulted trainee reads them once the turn's feedback is shared. The supervisor's own
review stays the official mark.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import circuit_topic, publish_after_commit
from app.features.roster import service as roster
from app.features.sittings import announcements, errors, repository, repository_run, schemas, service_floor
from app.features.sittings.service import _require_circuit, slot_and_circuit_for_owner

PEER_RATINGS = frozenset({"G", "A", "R"})  # the peer panel's Met / Partly / Not met; web `PEER_RATINGS`


def _items(structure: dict) -> set[str]:  # type: ignore[type-arg]
    """`domainId` and `domainId.competencyId` for every domain block of a scheme.

    The key shape is shared with web `peerItem` (`room/peerMarks.ts`): change both together.
    """
    found: set[str] = set()
    for block in structure.get("outline", []):
        if not isinstance(block, dict) or block.get("block") != "domain":
            continue
        found.add(str(block.get("id")))
        for competency in block.get("competencies", []):
            found.add(f"{block.get('id')}.{competency.get('id')}")
    return found


async def save_peer_marks(
    session: AsyncSession,
    circuit_id: uuid.UUID,
    slot_id: uuid.UUID,
    *,
    user_id: uuid.UUID,
    marks: list[schemas.PeerMarkIn],
) -> schemas.PeerMarksRead:
    """Save this trainee's marks on someone else's turn, then say what they have marked so far."""
    # `reviews` imports this slice, so its import has to wait until call time.
    from app.features.reviews import service_summary
    from app.features.rubrics import service_marking

    circuit = await repository_run.circuit_for_rostered_trainee(session, circuit_id, user_id)
    if circuit is None:
        raise errors.CircuitNotFound()
    await roster.ensure_rosterable(session, circuit.org_id, [user_id])
    if not await service_floor.is_training(session, circuit.id):
        raise errors.PeerMarksNotAllowed()
    slot = await repository.slot_by_id(session, circuit.org_id, slot_id)
    if slot is None or slot.circuit_id != circuit.id:
        raise errors.SlotNotFound()
    if slot.trainee_id == user_id:
        raise errors.PeerMarksOwnTurn()
    running = circuit.ended_at is None and circuit.active_slot_id == slot.id
    awaiting = slot.status == "completed" and not await service_summary.has_completed_review(
        session, circuit.org_id, slot.id
    )
    if not (running or awaiting):
        raise errors.PeerMarksClosed()
    version_id = await repository.rubric_version_for_slot(session, circuit.org_id, slot.id)
    known = _items(await service_marking.scheme_structure(session, version_id)) if version_id else set()
    if any(mark.item not in known for mark in marks):
        raise errors.PeerMarkItemUnknown()
    if any(mark.rating and mark.rating not in PEER_RATINGS for mark in marks):
        raise errors.PeerMarkRatingUnknown()
    await repository_run.upsert_peer_marks(
        session,
        org_id=circuit.org_id,
        circuit_id=circuit.id,
        slot_id=slot.id,
        marker_id=user_id,
        marks=[(mark.item, mark.rating or None, mark.comment or None) for mark in marks],
    )
    publish_after_commit(session, circuit_topic(circuit.id), announcements.PEER_MARKS_CHANGED)
    return await read_peer_marks(session, circuit.org_id, slot.id, marker_id=user_id)


async def read_peer_marks(
    session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID, *, marker_id: uuid.UUID | None = None
) -> schemas.PeerMarksRead:
    """Every peer mark on a slot (or one marker's), named by marker."""
    rows = list(await repository_run.peer_marks_for_slot(session, org_id, slot_id))
    if marker_id is not None:
        rows = [row for row in rows if row.marker_id == marker_id]
    names = await roster.names_for_users(session, org_id, sorted({row.marker_id for row in rows}, key=str))
    return schemas.PeerMarksRead(
        slot_id=slot_id,
        items=[
            schemas.PeerMarkRead(
                marker_id=row.marker_id,
                marker_name=names.get(row.marker_id, "A trainee"),
                item=row.item,
                rating=row.rating,
                comment=row.comment,
            )
            for row in rows
        ],
    )


async def peer_marks_for_staff(
    session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID, slot_id: uuid.UUID
) -> schemas.PeerMarksRead:
    """The supervisor's live view of every peer's marks on one slot of this circuit."""
    circuit = await _require_circuit(session, org_id, circuit_id)
    slot = await repository.slot_by_id(session, org_id, slot_id)
    if slot is None or slot.circuit_id != circuit.id:
        raise errors.SlotNotFound()
    return await read_peer_marks(session, org_id, slot_id)


async def read_my_peer_marks(
    session: AsyncSession, *, slot_id: uuid.UUID, user_id: uuid.UUID
) -> schemas.PeerMarksRead:
    """What the people who watched my practice turn marked, once its feedback is shared."""
    from app.features.reviews import service_summary  # call time: cycle

    pair = await slot_and_circuit_for_owner(session, slot_id, user_id)
    if pair is None:
        raise errors.SlotNotFound()
    slot, circuit = pair
    if not await service_floor.is_training(session, circuit.id):
        return schemas.PeerMarksRead(slot_id=slot_id, items=[])
    if not await service_summary.has_completed_review(session, slot.org_id, slot_id):
        return schemas.PeerMarksRead(slot_id=slot_id, items=[])
    return await read_peer_marks(session, slot.org_id, slot_id)
