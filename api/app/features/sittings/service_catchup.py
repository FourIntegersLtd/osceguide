"""Catching a circuit up from a read (S-7): the api advancing what the worker did not.

The worker's scheduled job and sweeper are the mechanism; this is for the day the
worker is down. A run screen calls it before it reads, and it takes the same step
the worker would (`service_run.advance`) against the sequence it just saw, so the
two can never both move a circuit: whoever gets the row lock second finds the
sequence changed and does nothing.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import savepoint
from app.core.errors import AppError
from app.core.logging import get_logger
from app.core.ports import RoomAgents
from app.core.settings import get_settings
from app.features.sittings import repository_run, service_run

log = get_logger(__name__)

# How far past its deadline a phase must be before anyone but the scheduled job
# moves it: the scheduled transition gets its moment first.
OVERDUE_GRACE_SECONDS = 15


async def advance_due(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    circuit_id: uuid.UUID | None = None,
    now: datetime,
    agents: RoomAgents,
) -> int:
    """Advance this organisation's overdue circuits (or one of them); returns how many moved.

    A circuit another advancer holds is skipped, not waited for: the reader would
    otherwise queue behind a dispatch to LiveKit. Each circuit is a savepoint, so
    one that cannot move is left for the next read. Only a refusal the service
    raises on purpose (`AppError`, such as the voice service being down) is
    absorbed; a bug still fails the read.
    """
    due = await repository_run.overdue_circuits(
        session, org_id=org_id, circuit_id=circuit_id, now=now, grace_seconds=OVERDUE_GRACE_SECONDS
    )
    agents, settings = agents, get_settings()
    moved = 0
    for row in due:
        try:
            async with savepoint(session):
                if not await repository_run.lock_circuit_unless_held(session, row.org_id, row.circuit_id):
                    continue
                if await service_run.advance(
                    session,
                    row.org_id,
                    row.circuit_id,
                    expected_seq=row.phase_seq,
                    agents=agents,
                    settings=settings,
                    now=now,
                ):
                    moved += 1
        except AppError:
            log.exception("read: advancing circuit failed", circuit_id=str(row.circuit_id))
    return moved
