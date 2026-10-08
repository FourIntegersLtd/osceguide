"""What every override to a running examination has in common.

The actions, the actor, the lock, and the record. They live here rather than in
one of the two override modules because both need them and neither owns them —
and because the list of actions is the audit's vocabulary, which should be
readable in one place.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.sittings import announcements, domain_run, errors, repository_run
from app.features.sittings.models import Circuit
from app.features.sittings.schemas import CircuitRead, Intervention, Interventions
from app.features.sittings.service import _require_circuit, read_circuit

# Actions, as they are written to `circuit_interventions`. Constants rather
# than literals at the call sites: the audit is read by somebody looking for
# what happened, and two spellings of one action is a gap in the record.
PAUSE = "pause"
RESUME = "resume"
EXTEND_CLOCK = "extend_clock"
RESET_CLOCK = "reset_clock"
RESEND_PATIENT = "resend_patient"
# The sweeper re-dispatching a patient who never arrived, once per station (R-17).
AUTO_RESEND_PATIENT = "auto_resend_patient"
REDO_STATION = "redo_station"
JUMP_TO = "jump_to"
ADVANCE = "advance"
AUTO_ADVANCE = "auto_advance"
# The reaper ending a circuit nobody closed: no human, so the record is the only notice (R-15).
AUTO_END = "auto_end"


@dataclass(frozen=True)
class Actor:
    """Who is overriding, and why, so the record names them both."""

    user_id: uuid.UUID | None
    reason: str | None = None

    @classmethod
    def for_user(cls, user_id: uuid.UUID | None, reason: str | None = None) -> Actor:
        """Built here rather than in the router, so a handler stays one call deep."""
        return cls(user_id=user_id, reason=reason)


async def live_for_update(session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID) -> Circuit:
    """The circuit, locked for the rest of the transaction, and actually running.

    Locked because every override reads the sequence and then writes it, and
    two supervisors on one examination would otherwise both think they had won.
    """
    circuit = await _require_circuit(session, org_id, circuit_id, lock=True)
    if circuit.started_at is None or circuit.ended_at is not None or not circuit.room_name:
        raise errors.CircuitNotLive()
    return circuit


async def write_intervention(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit: Circuit,
    *,
    action: str,
    actor: Actor,
    before: int,
    now: datetime,
    slot_id: uuid.UUID | None = None,
) -> None:
    """Record what was done, against the sequence it displaced.

    `before` and `before + 1` place the intervention against the transition it
    overtook, so a reader can see which scheduled move never happened.
    """
    await repository_run.record_intervention(
        session,
        org_id,
        circuit_id=circuit.id,
        slot_id=slot_id if slot_id is not None else circuit.active_slot_id,
        actor_user_id=actor.user_id,
        action=action,
        reason=actor.reason,
        phase_seq_before=before,
        phase_seq_after=before + 1,
        at=now,
    )


def current_step(circuit: Circuit) -> domain_run.Step:
    """The step the circuit is in now, so it can be restarted unchanged."""
    phase = domain_run.RunPhase(circuit.phase) if circuit.phase else None
    match phase:
        case domain_run.RunPhase.READING:
            return domain_run.Reading(slot_index=0)
        case domain_run.RunPhase.SIMULATION:
            return domain_run.Simulation(slot_index=0)
        case domain_run.RunPhase.BREAK:
            return domain_run.BreakStep(after_station=0)
        case _:
            raise errors.CircuitNotLive()


async def record_change(
    session: AsyncSession,
    org_id: uuid.UUID,
    circuit: Circuit,
    *,
    action: str,
    actor: Actor,
    before: int,
    now: datetime,
    event: str,
) -> CircuitRead:
    """Record an override, tell everyone watching, and hand back the circuit as it now reads."""
    await write_intervention(session, org_id, circuit, action=action, actor=actor, before=before, now=now)
    await announcements.circuit_changed(session, org_id, circuit.id, name=event)
    return await read_circuit(session, org_id, circuit.id)


async def list_interventions(
    session: AsyncSession, org_id: uuid.UUID, circuit_id: uuid.UUID
) -> Interventions:
    """Everything a human has done to this circuit, and why, in order."""
    await _require_circuit(session, org_id, circuit_id)
    interventions = await repository_run.interventions_for_circuit(session, org_id, circuit_id)
    return Interventions(
        items=[
            Intervention(
                id=intervention.id,
                circuit_id=intervention.circuit_id,
                slot_id=intervention.slot_id,
                actor_user_id=intervention.actor_user_id,
                action=intervention.action,
                reason=intervention.reason,
                phase_seq_before=intervention.phase_seq_before,
                phase_seq_after=intervention.phase_seq_after,
                at=intervention.at,
            )
            for intervention in interventions
        ]
    )
