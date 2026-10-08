"""Assembling the exam-day board.

Reads through other slices' services, never their tables, like everything else
in this slice. The clock arithmetic and the alert rules belong to `sittings` and
are used from there rather than reimplemented here — a board that decided for
itself when a phase was overdue would be a second opinion about the time.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import service_reads as attempts
from app.features.dashboard.schemas_live import LiveBoard, LiveCircuit, LivePerson, LiveRunRead, LiveStation
from app.features.health import service as health
from app.features.identity import service as identity
from app.features.sittings import service_catchup
from app.features.sittings import service_reads as sittings
from app.features.stations import service_reads as stations


async def build_live_board(session: AsyncSession, org_id: uuid.UUID, *, now: datetime) -> LiveBoard:
    """Every circuit this organisation has running, with its clock and its alerts."""
    # The board is what the api reads when the worker is down: advance first, then show.
    await service_catchup.advance_due(session, org_id=org_id, now=now)
    worker_running = await health.worker_running(session, now=now)
    details = await sittings.live_circuits(session, org_id)
    if not details:
        return LiveBoard(as_of=now, circuits=[], worker_running=worker_running)

    slot_ids = [slot.id for detail in details for slot in detail.slots]
    user_ids = {slot.trainee_id for detail in details for slot in detail.slots}
    user_ids |= {detail.circuit.supervisor_user_id for detail in details if detail.circuit.supervisor_user_id}
    version_ids = [slot.station_version_id for detail in details for slot in detail.slots]

    people = await identity.user_refs_by_ids(session, list(user_ids))
    live = await attempts.live_attempts_for_slots(session, slot_ids)
    titles = await stations.summaries_by_version_id(session, org_id, version_ids)

    def person(user_id: uuid.UUID) -> LivePerson:
        """One person's name and email, from the batch already fetched above."""
        ref = people.get(user_id)
        return LivePerson(
            user_id=user_id,
            name=ref.name if ref else None,
            email=ref.email if ref else None,
        )

    circuits = []
    for detail in details:
        circuit = detail.circuit
        active = next((slot for slot in detail.slots if slot.id == circuit.active_slot_id), None)
        attempt = live.get(active.id) if active else None
        summary = titles.get(active.station_version_id) if active else None

        circuits.append(
            LiveCircuit(
                circuit_id=circuit.id,
                circuit_name=circuit.name,
                sitting_id=detail.sitting.id,
                sitting_name=detail.sitting.name,
                mode=detail.sitting.mode,
                room_name=circuit.room_name,
                supervisor=(person(circuit.supervisor_user_id) if circuit.supervisor_user_id else None),
                # Deduplicated in slot order: an exam circuit is one candidate
                # at every station, so the raw list would name them twelve times.
                candidates=[person(user_id) for user_id in _candidates(detail)],
                current_station=(
                    LiveStation(
                        slot_id=active.id,
                        slot_index=active.slot_index,
                        title=summary.title if summary else None,
                    )
                    if active
                    else None
                ),
                phase=circuit.phase,
                phase_started_at=circuit.phase_started_at,
                phase_ends_at=circuit.phase_ends_at,
                paused=circuit.paused_at is not None,
                auto_advance=circuit.auto_advance,
                elapsed_seconds=sittings.elapsed_seconds(
                    circuit.phase_started_at,
                    paused_seconds=circuit.paused_seconds,
                    paused_at=circuit.paused_at,
                    now=now,
                ),
                remaining_seconds=sittings.remaining_seconds(
                    circuit.phase_ends_at, paused_at=circuit.paused_at, now=now
                ),
                stations_total=len(detail.slots),
                stations_completed=sum(
                    1 for slot in detail.slots if slot.status in sittings.FINISHED_SLOT_STATUSES
                ),
                attempt_id=attempt.id if attempt else None,
                attempt_status=attempt.status if attempt else None,
                alerts=sittings.alerts_for(
                    phase=circuit.phase,
                    phase_started_at=circuit.phase_started_at,
                    phase_ends_at=circuit.phase_ends_at,
                    paused_at=circuit.paused_at,
                    attempt_status=attempt.status if attempt else None,
                    auto_advance=circuit.auto_advance,
                    now=now,
                    voice_fault=circuit.voice_fault_at is not None,
                ),
            )
        )
    return LiveBoard(as_of=now, circuits=circuits, worker_running=worker_running)


async def list_run_history(
    session: AsyncSession, org_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None
) -> tuple[list[LiveRunRead], str | None]:
    """The board's past: circuits this organisation has finished, most recent first.

    The live board only knows what is running; each row here was written by
    `sittings` at the moment a circuit ended.
    """
    runs, next_cursor = await sittings.run_history(session, org_id, limit=limit, cursor=cursor)
    supervisors = await identity.user_refs_by_ids(
        session, list({run.supervisor_user_id for run in runs if run.supervisor_user_id})
    )

    def supervisor(user_id: uuid.UUID | None) -> LivePerson | None:
        """The supervisor's name and email, from the batch fetched above."""
        if user_id is None:
            return None
        ref = supervisors.get(user_id)
        return LivePerson(user_id=user_id, name=ref.name if ref else None, email=ref.email if ref else None)

    return [
        LiveRunRead(
            id=run.id,
            circuit_id=run.circuit_id,
            circuit_name=run.circuit_name,
            sitting_id=run.sitting_id,
            sitting_name=run.sitting_name,
            mode=run.mode,
            supervisor=supervisor(run.supervisor_user_id),
            started_at=run.started_at,
            ended_at=run.ended_at,
            candidate_count=run.candidate_count,
            stations_total=run.stations_total,
            stations_completed=run.stations_completed,
            status=run.status,
        )
        for run in runs
    ], next_cursor


def _candidates(detail: sittings.CircuitDetail) -> list[uuid.UUID]:
    """Each candidate once, in the order their first station falls."""
    seen: list[uuid.UUID] = []
    for slot in detail.slots:
        if slot.trainee_id not in seen:
            seen.append(slot.trainee_id)
    return seen
