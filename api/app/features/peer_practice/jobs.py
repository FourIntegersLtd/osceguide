"""Matching people who are waiting, and marking what they did.

Two queues, because they fail differently. Matching is quick and idempotent and
runs every minute whether or not anybody joined. Transcription waits on an
upload it does not control, costs a model call, and must not be retried into a
second attempt for the same session — hence the queueing lock keyed on the
session and the state guard in `service_feedback`.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audience import Audience, Visibility
from app.core.jobs import defer_in_transaction, get_jobs_app
from app.core.logging import get_logger

log = get_logger(__name__)

MATCHING_QUEUE = "matching"
TRY_MATCH_TASK = "try_match_practice_room"
TRANSCRIPTION_QUEUE = "transcription"
TRANSCRIBE_TASK = "transcribe_peer_session"

# Egress finishes writing after it is told to stop. Waiting is the normal case,
# not the exceptional one, so the first look is deliberately late.
FIRST_LOOK_SECONDS = 30
RETRY_SECONDS = 30
MAX_LOOKS = 20


def audience_lock_key(exam_id: uuid.UUID, audience: Audience) -> str:
    """A queueing-lock key naming one exam room, so only one matcher nudge runs for it at a time."""
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


async def enqueue_transcription(
    session: AsyncSession, *, session_id: uuid.UUID, now: datetime, attempt: int = 0
) -> None:
    """Queue the marking of a finished session, in the caller's transaction.

    The lock carries the attempt number so a reschedule is not refused as a
    duplicate of the job that scheduled it, while two callers stopping the same
    recording still collapse into one.
    """
    await defer_in_transaction(
        session,
        queue=TRANSCRIPTION_QUEUE,
        task=TRANSCRIBE_TASK,
        queueing_lock=f"transcribe:{session_id}:{attempt}",
        ignore_lock_conflict=True,
        scheduled_at=now + timedelta(seconds=FIRST_LOOK_SECONDS if attempt == 0 else RETRY_SECONDS),
        args={"session_id": str(session_id), "attempt": attempt},
    )


async def drain_waiting_room(session: AsyncSession, exam_id: uuid.UUID, *, audience: Audience) -> int:
    """Pair everyone who can be paired in one room. Returns how many pairs were made."""
    from app.features.peer_practice.service import match_waiting

    made = 0
    while await match_waiting(session, exam_id, audience=audience) is not None:
        made += 1
    return made


def register() -> None:
    """Wire up this slice's background jobs: matching nudges and the periodic sweeps."""
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

    @app.task(name=TRANSCRIBE_TASK, queue=TRANSCRIPTION_QUEUE)
    async def transcribe_peer_session(session_id: str, attempt: int = 0) -> None:
        """Transcribe a finished consultation and put it through marking.

        A recording that has not landed yet reschedules rather than fails: the
        upload is LiveKit's, on its own clock, and a session whose audio was
        three minutes late is still a session somebody wants feedback on. After
        `MAX_LOOKS` it is given up on and said so on the row, because a
        recording that never arrived is not one that will.
        """
        from app.core.db import job_session, savepoint
        from app.features.peer_practice import repository_sessions, service_feedback

        practice_id = uuid.UUID(session_id)
        async with job_session() as session:
            now = datetime.now(UTC)
            try:
                async with savepoint(session):
                    await service_feedback.build_feedback(session, practice_id, now=now)
            except service_feedback.RecordingNotReady:
                if attempt >= MAX_LOOKS:
                    await repository_sessions.set_recording_state(
                        session, practice_id, state="failed", error="the recording never arrived"
                    )
                    log.warning("peer recording never arrived", session_id=session_id)
                    return
                await enqueue_transcription(session, session_id=practice_id, now=now, attempt=attempt + 1)
            except Exception:  # noqa: BLE001 - any other failure is the end of the road, said on the row
                log.exception("peer session not marked", session_id=session_id)
                await repository_sessions.set_recording_state(
                    session, practice_id, state="failed", error="marking failed"
                )

    @app.periodic(cron="* * * * *")
    @app.task(name="match_practice_queue", queue="matching")
    async def match_practice_queue(timestamp: int = 0) -> None:
        """Pair whoever is waiting, in every room of every exam.

        Periodic rather than only on join: two people arriving at the same
        moment would otherwise both try to match and find an empty queue.
        Rooms are walked separately, so a trainee waiting inside their
        institution is never paired with a stranger.
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
