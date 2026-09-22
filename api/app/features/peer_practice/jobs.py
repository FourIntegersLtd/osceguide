"""Matching people who are waiting."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audience import Audience, Visibility
from app.core.jobs import defer_in_transaction, get_jobs_app
from app.core.logging import get_logger

log = get_logger(__name__)

MATCHING_QUEUE = "matching"
TRY_MATCH_TASK = "try_match_practice_room"


def audience_lock_key(exam_id: uuid.UUID, audience: Audience) -> str:
    org = str(audience.org_id) if audience.org_id else ""
    group = str(audience.group_id) if audience.group_id else ""
    return f"match:{exam_id}:{audience.visibility}:{org}:{group}"


async def enqueue_try_match(session: AsyncSession, *, exam_id: uuid.UUID, audience: Audience) -> None:
    """Nudge the matcher after somebody joins, without waiting for the cron.

    A second join for the same exam and audience while the first job is still
    waiting hits the queueing-lock unique constraint. That is the lock doing
    its job — one nudge is enough — so the duplicate is silently ignored.
    """
    await defer_in_transaction(
        session,
        queue=MATCHING_QUEUE,
        task=TRY_MATCH_TASK,
        queueing_lock=audience_lock_key(exam_id, audience),
        ignore_lock_conflict=True,
        args={
            "exam_id": str(exam_id),
            "visibility": str(audience.visibility),
            "org_id": str(audience.org_id) if audience.org_id else None,
            "group_id": str(audience.group_id) if audience.group_id else None,
        },
    )


async def drain_waiting_room(session: AsyncSession, exam_id: uuid.UUID, *, audience: Audience) -> int:
    """Pair everyone who can be paired in one room. Returns how many pairs were made."""
    from app.features.peer_practice.service import match_waiting

    made = 0
    while await match_waiting(session, exam_id, audience=audience) is not None:
        made += 1
    return made


def register() -> None:
    app = get_jobs_app()

    @app.task(name=TRY_MATCH_TASK, queue=MATCHING_QUEUE)
    async def try_match_practice_room(
        exam_id: str,
        visibility: str,
        org_id: str | None = None,
        group_id: str | None = None,
    ) -> None:
        """One nudge for a single exam room after a join."""
        from app.core.db import job_session

        audience = Audience(
            visibility=Visibility(visibility),
            org_id=uuid.UUID(org_id) if org_id else None,
            group_id=uuid.UUID(group_id) if group_id else None,
        )
        async with job_session() as session:
            count = await drain_waiting_room(session, uuid.UUID(exam_id), audience=audience)
            if count:
                log.info("practice pairs matched on join nudge", exam_id=exam_id, pairs=count)

    @app.periodic(cron="* * * * *")
    @app.task(name="match_practice_queue", queue="matching")
    async def match_practice_queue(timestamp: int = 0) -> None:
        """Pair whoever is waiting, in every room of every exam.

        Periodic rather than only on join: two people arriving at the same
        moment would otherwise both try to match, and one of them would find an
        empty queue. Join still enqueues a nudge so pairing is immediate when
        the worker is up.

        Rooms are walked separately. Matching an exam as one pool would pair a
        trainee waiting inside their institution with a stranger, which is the
        thing an audience exists to prevent.
        """
        from app.core.db import job_session
        from app.features.catalog import service as catalog
        from app.features.peer_practice import repository

        async with job_session() as session:
            for exam in await catalog.exam_refs(session):
                for audience in await repository.waiting_audiences(session, exam.id):
                    count = await drain_waiting_room(session, exam.id, audience=audience)
                    if count:
                        log.info(
                            "practice pair matched",
                            exam=exam.code,
                            room=str(audience.visibility),
                            pairs=count,
                        )

    @app.periodic(cron="* * * * *")
    @app.task(name="expire_practice_queue", queue="matching")
    async def expire_practice_queue(timestamp: int = 0) -> None:
        """Mark queue places that waited too long as expired."""
        from datetime import UTC, datetime

        from app.core.db import job_session
        from app.features.peer_practice import repository

        async with job_session() as session:
            expired = await repository.expire_stale_waiting(session, at=datetime.now(UTC))
            if expired:
                log.info("practice queue entries expired", count=expired)
