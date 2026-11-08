"""The marking scheme of the station running now, for the people watching a training room.

Training only, and only while a station runs. The supervisor sees it, and so does a trainee
who is not the one sitting it; the person sitting it reads their brief instead. An exam never
shows its scheme to anybody in the room.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.roster import service as roster
from app.features.rubrics import service_marking
from app.features.sittings import errors, repository, repository_run, service_floor
from app.features.sittings.models import Circuit
from app.features.sittings.schemas import SchemeRead
from app.features.sittings.service import _require_circuit


async def scheme_for_staff(session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID) -> SchemeRead:
    """The scheme of the station running now, for the supervisor's side panel."""
    circuit = await _require_circuit(session, org_id, circuit_id)
    return await _scheme(session, circuit)


async def scheme_for_trainee(
    session: AsyncSession, circuit_id: uuid.UUID, *, user_id: uuid.UUID
) -> SchemeRead:
    """A rostered trainee waiting for their turn. 404 for anybody not on the circuit."""
    circuit = await repository_run.circuit_for_rostered_trainee(session, circuit_id, user_id)
    if circuit is None:
        raise errors.CircuitNotFound()
    await roster.ensure_rosterable(session, circuit.org_id, [user_id])
    if await service_floor.active_trainee_id(session, circuit.org_id, circuit) == user_id:
        raise errors.SchemeNotShown()
    return await _scheme(session, circuit)


async def _scheme(session: AsyncSession, circuit: Circuit) -> SchemeRead:
    """The running station's scheme, only in training and only while a station is on."""
    if not await service_floor.is_training(session, circuit.id):
        raise errors.SchemeNotShown()
    if circuit.started_at is None or circuit.ended_at is not None or circuit.active_slot_id is None:
        raise errors.NoActiveStation()
    version_id = await repository.rubric_version_for_slot(session, circuit.org_id, circuit.active_slot_id)
    if version_id is None:
        raise errors.NoActiveStation()
    structure = await service_marking.scheme_structure(session, version_id)
    return SchemeRead(slot_id=circuit.active_slot_id, structure=_for_display(structure))


_DOMAIN_SHOWN = ("id", "title", "description", "scale", "optional")
_COMPETENCY_SHOWN = ("id", "label", "title")


def _picked(source: Any, keys: tuple[str, ...]) -> dict[str, Any]:
    """Only the listed keys of an object; anything else, including a key added later, is left out."""
    return {key: source[key] for key in keys if isinstance(source, dict) and key in source}


def _for_display(structure: dict[str, Any]) -> dict[str, Any]:
    """What a trainee may see of a scheme: each domain's name, scale and competency names, nothing else.

    An allowlist: the marker's instructions, notes sections, per-competency feedback, advanced
    settings and live flags stay with the examiner, and a field added to a scheme later is hidden
    until someone lists it here.
    """
    outline = []
    for block in structure.get("outline", []):
        if not isinstance(block, dict) or block.get("block") != "domain":
            continue
        shown = {"block": "domain", **_picked(block, _DOMAIN_SHOWN)}
        if isinstance(block.get("competencies"), list):
            shown["competencies"] = [
                _picked(competency, _COMPETENCY_SHOWN) for competency in block["competencies"]
            ]
        outline.append(shown)
    return {
        "schemaVersion": structure.get("schemaVersion"),
        "scales": structure.get("scales"),
        "outline": outline,
    }
