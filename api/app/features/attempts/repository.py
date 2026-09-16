"""Storage for attempts, their turns and their results.

Attempts are not org-scoped in the usual way: a consumer attempt has no
organisation at all. The org-scoped reads say so in their names, and the
worker-facing reads take an attempt id because that is all a worker is given.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import encode_cursor
from app.features.attempts.models import Attempt


async def create_attempt(
    session: AsyncSession,
    *,
    kind: str,
    user_id: uuid.UUID,
    exam_id: uuid.UUID,
    org_id: uuid.UUID | None = None,
    station_version_id: uuid.UUID | None = None,
    slot_id: uuid.UUID | None = None,
    set_entry_id: uuid.UUID | None = None,
    peer_session_id: uuid.UUID | None = None,
    source_attempt_id: uuid.UUID | None = None,
    room_name: str | None = None,
) -> Attempt:
    attempt = Attempt(
        kind=kind,
        user_id=user_id,
        exam_id=exam_id,
        org_id=org_id,
        station_version_id=station_version_id,
        slot_id=slot_id,
        set_entry_id=set_entry_id,
        peer_session_id=peer_session_id,
        source_attempt_id=source_attempt_id,
        room_name=room_name,
    )
    session.add(attempt)
    await session.flush()
    await session.refresh(attempt)
    return attempt


async def attempt_by_id(session: AsyncSession, attempt_id: uuid.UUID) -> Attempt | None:
    return (await session.execute(select(Attempt).where(Attempt.id == attempt_id))).scalar_one_or_none()


async def live_attempt_for_slot(session: AsyncSession, slot_id: uuid.UUID) -> Attempt | None:
    stmt = select(Attempt).where(Attempt.slot_id == slot_id, Attempt.status != "failed")
    return (await session.execute(stmt)).scalar_one_or_none()


async def set_status(
    session: AsyncSession,
    attempt_id: uuid.UUID,
    *,
    status: str,
    at: datetime,
    reason: str | None = None,
) -> None:
    values: dict[str, Any] = {"status": status}
    if status == "running":
        values["started_at"] = at
    elif status == "interaction_complete":
        values["completed_at"] = at
    elif status == "failed":
        values["failed_reason"] = reason
    await session.execute(update(Attempt).where(Attempt.id == attempt_id).values(**values))


async def freeze_definition(
    session: AsyncSession, attempt_id: uuid.UUID, *, definition: dict[str, Any], at: datetime
) -> None:
    """Write the rendered definition once.

    Guarded on `definition IS NULL` in the statement itself rather than by a
    read-then-write, so two workers racing to bootstrap the same attempt cannot
    both believe they were first.
    """
    await session.execute(
        update(Attempt)
        .where(Attempt.id == attempt_id, Attempt.definition.is_(None))
        .values(definition=definition, definition_frozen_at=at)
    )


async def delete_attempt(session: AsyncSession, attempt_id: uuid.UUID) -> None:
    from sqlalchemy import delete

    await session.execute(delete(Attempt).where(Attempt.id == attempt_id))


async def list_for_user(
    session: AsyncSession, user_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None = None
) -> tuple[list[Attempt], str | None]:
    stmt = select(Attempt).where(Attempt.user_id == user_id)
    if cursor:
        stmt = stmt.where(Attempt.created_at < datetime.fromisoformat(cursor["t"]))
    rows = list(
        (
            await session.execute(
                stmt.order_by(Attempt.created_at.desc(), Attempt.id.desc()).limit(limit + 1)
            )
        ).scalars()
    )
    if len(rows) <= limit:
        return rows, None
    page = rows[:limit]
    return page, encode_cursor({"t": page[-1].created_at, "i": str(page[-1].id)})


async def defer_job(
    session: AsyncSession,
    *,
    queue: str,
    task: str,
    args: dict[str, Any],
    queueing_lock: str,
) -> None:
    """Write a queue row in the caller's transaction.

    procrastinate's own connector holds a separate pool, so deferring through it
    would commit the job on another connection — and the guarantee in ADR 0006
    that a job and the data justifying it land together would quietly not hold.
    Calling its SQL function on our session keeps one transaction; the queueing
    lock makes a redelivered message idempotent.
    """
    await session.execute(
        text(
            "SELECT procrastinate_defer_jobs_v1(ARRAY[ROW("
            ":queue, :task, :priority, NULL, :queueing_lock, CAST(:args AS jsonb), NULL"
            ")]::procrastinate_job_to_defer_v1[])"
        ),
        {
            "queue": queue,
            "task": task,
            "priority": 0,
            "queueing_lock": queueing_lock,
            "args": json.dumps(args),
        },
    )


async def trial_counts(session: AsyncSession, user_id: uuid.UUID, exam_id: uuid.UUID) -> tuple[int, int]:
    """`(set stations used, attempts completed)` for the free-trial rule.

    Counted per exam, not per account. b2c held a person as four separate user
    documents, one per product, each with its own trial — so somebody who used
    their SCA trial still had a PLAB one. Counting across the unified account
    would quietly take that away from everybody mid-migration.
    """
    set_stations = await session.scalar(
        select(func.count())
        .select_from(Attempt)
        .where(
            Attempt.user_id == user_id,
            Attempt.exam_id == exam_id,
            Attempt.kind == "set_station",
        )
    )
    completed = await session.scalar(
        select(func.count())
        .select_from(Attempt)
        .where(
            Attempt.user_id == user_id,
            Attempt.exam_id == exam_id,
            Attempt.status.in_(("interaction_complete", "evaluated")),
        )
    )
    return int(set_stations or 0), int(completed or 0)
