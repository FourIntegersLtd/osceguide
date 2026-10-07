"""The bell, as background work.

Two tasks. `advance_circuit` is the bell itself: one job per phase, scheduled
for the moment that phase ends, carrying the sequence it was scheduled
against. `sweep_circuits` is the safety net.

The sweeper is not the mechanism. If it were, every transition would be up to a
minute late. It exists for the cases the scheduled job cannot cover: the job
worker was down when a phase ended, a transition raised and rolled back, or a
deploy landed mid-examination. Without it a single lost job stops a circuit
dead, and the first anybody knows is a candidate sitting in silence.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from functools import partial
from typing import Any, TypeVar

from procrastinate import RetryStrategy
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jobs import get_jobs_app
from app.core.logging import get_logger
from app.core.ports import RoomAgents
from app.core.settings import Settings, get_settings
from app.features.sittings import repository_run, service_clock, service_patient, service_run

T = TypeVar("T")

log = get_logger(__name__)

SWEEP_QUEUE = "circuits"
SWEEP_TASK = "sweep_circuits"

# How far past its deadline a phase must be before the sweeper steps in. Short
# enough that a candidate does not wait, long enough that the scheduled
# transition gets its moment first and the two do not race for every phase.
SWEEP_GRACE_SECONDS = 15

# Doubling waits, 12 tries: about 2 hours of LiveKit outage before the job gives up.
CLEAR_ROOM_RETRY = RetryStrategy(max_attempts=12, exponential_wait=2)


async def advance_one(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    circuit_id: uuid.UUID,
    expected_seq: int | None,
    agents: RoomAgents,
    settings: Settings,
    now: datetime,
) -> bool:
    """One transition, as its own unit of work.

    Separate from the task body so a test can run it without a queue, and so
    the sweeper and the scheduled job share one path rather than two that drift.
    """
    return await service_run.advance(
        session,
        org_id,
        circuit_id,
        expected_seq=expected_seq,
        agents=agents,
        settings=settings,
        now=now,
    )


async def sweep_now(
    *,
    agents: RoomAgents,
    settings: Settings,
    now: datetime,
    open_session: object = None,
) -> tuple[int, int, int]:
    """Catch up every circuit the clock has got ahead of, and close the abandoned.

    One transaction per circuit, deliberately: a circuit whose dispatch fails
    must not roll back the eleven that were fine, and a lock held across every
    live examination in the deployment would serialise exam day. For the same
    reason one circuit that raises is logged and skipped, never allowed to end
    the sweep: the job succeeds, the failing circuit is found in the logs by
    its id and tried again next minute.

    Returns `(advanced, ended, failed)`.
    """
    from app.core.db import job_session

    opener = open_session or job_session

    async with opener() as session:  # type: ignore[operator]
        due = await repository_run.overdue_circuits(session, now=now, grace_seconds=SWEEP_GRACE_SECONDS)
        stale = await repository_run.stale_circuits(session, quiet_since=now - service_run.STALE_AFTER)

    advanced = 0
    ended = 0
    failed = 0
    for overdue_circuit in due:
        completed, moved = await _one_circuit(
            "advancing circuit",
            overdue_circuit.circuit_id,
            partial(
                advance_one,
                org_id=overdue_circuit.org_id,
                circuit_id=overdue_circuit.circuit_id,
                expected_seq=overdue_circuit.phase_seq,
                agents=agents,
                settings=settings,
                now=now,
            ),
            opener=opener,
        )
        if not completed:
            failed += 1
        elif moved:
            advanced += 1
            log.info("swept an overdue circuit forward", circuit_id=str(overdue_circuit.circuit_id))

    for stale_circuit in stale:
        completed, _ = await _one_circuit(
            "ending circuit",
            stale_circuit.circuit_id,
            partial(
                service_run.end_abandoned,
                org_id=stale_circuit.org_id,
                circuit_id=stale_circuit.circuit_id,
                agents=agents,
                now=now,
            ),
            opener=opener,
        )
        if not completed:
            failed += 1
        else:
            ended += 1
            log.info("ended a circuit left running overnight", circuit_id=str(stale_circuit.circuit_id))

    if advanced or ended or failed:
        log.info("circuits swept", advanced=advanced, ended=ended, failed=failed)
    return advanced, ended, failed


def register() -> None:
    """Declare the tasks with procrastinate.

    Behind a function so importing this module for its logic — which the tests
    do — needs no configured queue.
    """
    app = get_jobs_app()

    @app.task(name=service_clock.ADVANCE_TASK, queue=service_clock.ADVANCE_QUEUE)
    async def advance_circuit(org_id: str, circuit_id: str, expected_seq: int) -> None:
        """The scheduled job for one phase ending: move the circuit on if `expected_seq` still matches."""
        from app.core.db import job_session
        from app.features.voice.service import get_room_agents

        async with job_session() as session:
            await advance_one(
                session,
                org_id=uuid.UUID(org_id),
                circuit_id=uuid.UUID(circuit_id),
                expected_seq=expected_seq,
                agents=get_room_agents(),
                settings=get_settings(),
                now=datetime.now(UTC),
            )

    @app.task(
        name=service_patient.CLEAR_ROOM_TASK,
        queue=service_patient.CLEAR_ROOM_QUEUE,
        retry=CLEAR_ROOM_RETRY,
    )
    async def clear_room_agents(room: str, circuit_id: str) -> None:
        """Take the patient out of an ended circuit's room; raises, and so retries, while LiveKit is down."""
        from app.features.voice.service import clear_agents_from_room, get_room_agents

        await clear_agents_from_room(agents=get_room_agents(), room=room)

    @app.periodic(cron="* * * * *")
    @app.task(name=SWEEP_TASK, queue=SWEEP_QUEUE)
    async def sweep_circuits(timestamp: int = 0) -> None:
        """The minute-by-minute safety net that runs `sweep_now`."""
        from app.features.voice.service import get_room_agents

        await sweep_now(agents=get_room_agents(), settings=get_settings(), now=datetime.now(UTC))


async def _one_circuit(
    label: str,
    circuit_id: uuid.UUID,
    step: Callable[[Any], Awaitable[T]],
    *,
    opener: Any,
) -> tuple[bool, T | None]:
    """Run `step` for one circuit in its own transaction.

    Answers `(True, result)`, or `(False, None)` when the step raised: the
    failure is logged with the circuit id and the sweep carries on with the next.
    """
    try:
        async with opener() as session:
            return True, await step(session)
    except Exception:
        log.exception(f"sweep: {label} failed", circuit_id=str(circuit_id))
        return False, None
