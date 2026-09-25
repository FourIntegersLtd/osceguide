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
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jobs import get_jobs_app
from app.core.logging import get_logger
from app.core.ports import RoomAgents
from app.core.settings import Settings, get_settings
from app.features.sittings import repository_run, service_clock, service_run

log = get_logger(__name__)

SWEEP_QUEUE = "circuits"
SWEEP_TASK = "sweep_circuits"

# How far past its deadline a phase must be before the sweeper steps in. Short
# enough that a candidate does not wait, long enough that the scheduled
# transition gets its moment first and the two do not race for every phase.
SWEEP_GRACE_SECONDS = 15


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
) -> tuple[int, int]:
    """Catch up every circuit the clock has got ahead of, and close the abandoned.

    One transaction per circuit, deliberately: a circuit whose dispatch fails
    must not roll back the eleven that were fine, and a lock held across every
    live examination in the deployment would serialise exam day.

    Returns `(advanced, reaped)`.
    """
    from app.core.db import job_session

    opener = open_session or job_session

    async with opener() as session:  # type: ignore[operator]
        due = await repository_run.overdue_circuits(session, now=now, grace_seconds=SWEEP_GRACE_SECONDS)
        stale = await repository_run.stale_circuits(session, started_before=now - service_run.STALE_AFTER)

    advanced = 0
    for row in due:
        async with opener() as session:  # type: ignore[operator]
            moved = await advance_one(
                session,
                org_id=row.org_id,
                circuit_id=row.circuit_id,
                expected_seq=row.phase_seq,
                agents=agents,
                settings=settings,
                now=now,
            )
        if moved:
            advanced += 1
            log.info("swept an overdue circuit forward", circuit_id=str(row.circuit_id))

    reaped = 0
    stale_ids = {row.circuit_id for row in stale}
    for row in stale:
        async with opener() as session:  # type: ignore[operator]
            await service_run.end_circuit(session, row.org_id, row.circuit_id, agents=agents, now=now)
        reaped += 1
        log.info("ended a circuit left running overnight", circuit_id=str(row.circuit_id))

    if advanced or stale_ids:
        log.info("circuits swept", advanced=advanced, reaped=reaped)
    return advanced, reaped


def register() -> None:
    """Declare the tasks with procrastinate.

    Behind a function so importing this module for its logic — which the tests
    do — needs no configured queue.
    """
    app = get_jobs_app()

    @app.task(name=service_clock.ADVANCE_TASK, queue=service_clock.ADVANCE_QUEUE)
    async def advance_circuit(org_id: str, circuit_id: str, expected_seq: int) -> None:
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

    @app.periodic(cron="* * * * *")
    @app.task(name=SWEEP_TASK, queue=SWEEP_QUEUE)
    async def sweep_circuits(timestamp: int = 0) -> None:
        from app.features.voice.service import get_room_agents

        await sweep_now(agents=get_room_agents(), settings=get_settings(), now=datetime.now(UTC))
