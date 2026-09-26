"""Turning a recorded peer consultation into a marked attempt.

A peer session becomes an attempt: its transcript is delivered into the same
pipeline that marks every AI mock — rubric freeze, marking queue, result
read, live stream — rather than a second pipeline for people who practised
with a partner.

Only the doctor is scored; the rubric is written for the doctor's performance.
The patient's half of the session is the peer rating they give each other.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import publish_after_commit, user_topic
from app.core.logging import get_logger
from app.core.ports import Transcriber, TranscriptionFailed
from app.core.settings import get_settings
from app.features.attempts import service as attempts
from app.features.attempts import service_offline
from app.features.catalog import service as catalog
from app.features.entitlements.errors import NotEntitled
from app.features.media_production import service_storage as storage
from app.features.peer_practice import diariser, repository_sessions
from app.features.peer_practice.service_lifecycle import SESSION_UPDATED

log = get_logger(__name__)


class RecordingNotReady(Exception):
    """The egress has not finished uploading yet. Try again shortly."""


async def build_feedback(
    session: AsyncSession,
    session_id: uuid.UUID,
    *,
    now: datetime,
    transcriber: Transcriber | None = None,
    diarise: Callable[[str], Awaitable[list[dict[str, str]]]] | None = None,
) -> uuid.UUID | None:
    """Transcribe a finished session and put the doctor's half through marking.

    Answers the attempt id, or `None` when there was nothing to do. Raises
    `RecordingNotReady` when the audio has not landed yet, which the job turns
    into a reschedule rather than a failure — egress upload lags the stop by
    seconds and occasionally by more.
    """
    practice_session = await repository_sessions.session_by_id(session, session_id)
    if practice_session is None or practice_session.recording_state not in {"stopped", "transcribing"}:
        return None
    if practice_session.doctor_attempt_id is not None or not practice_session.recording_key:
        return None

    settings = get_settings()
    if not storage.object_exists(settings, practice_session.recording_key):
        raise RecordingNotReady(practice_session.recording_key)

    await repository_sessions.set_recording_state(session, session_id, state="transcribing")
    exam_code = await catalog.exam_code_by_id(session, practice_session.exam_id) or ""

    try:
        audio_url = storage.readable_url(settings, practice_session.recording_key)
        raw = await (transcriber or _transcriber()).transcribe(audio_url=audio_url)
        turns = await (diarise or diariser.to_turns)(raw)
    except TranscriptionFailed as exc:
        await _failed(session, session_id, reason=str(exc))
        return None

    try:
        attempt_read = await attempts.start_attempt(
            session,
            user_id=practice_session.doctor_user_id,
            kind="peer",
            exam_code=exam_code,
            now=now,
            station_version_id=practice_session.station_version_id,
            peer_session_id=practice_session.id,
            room_name=practice_session.room_name,
        )
    except NotEntitled as exc:
        # The practice already happened. Refusing it after the fact helps
        # nobody, and charging for it retroactively is not this code's call —
        # so it is recorded as unmarked and said plainly on the session.
        await _failed(session, session_id, reason=f"not entitled when marking: {exc}")
        return None

    await service_offline.mark_delivered_transcript(
        session,
        attempt_read.id,
        turns=turns,
        runtime_label="peer_practice",
        now=now,
    )

    await repository_sessions.set_doctor_attempt(session, session_id, attempt_id=attempt_read.id)
    publish_after_commit(
        session, user_topic(practice_session.doctor_user_id), SESSION_UPDATED, {"session_id": str(session_id)}
    )
    log.info(
        "peer session marked", session_id=str(session_id), attempt_id=str(attempt_read.id), turns=len(turns)
    )
    return attempt_read.id


async def _failed(session: AsyncSession, session_id: uuid.UUID, *, reason: str) -> None:
    """Record that marking failed, and log why, so support can see it without a stack trace."""
    log.warning("peer session not marked", session_id=str(session_id), reason=reason)
    await repository_sessions.set_recording_state(session, session_id, state="failed", error=reason[:200])


def _transcriber() -> Transcriber:
    """The real transcriber, built on demand so tests can pass a fake instead."""
    from app.features.peer_practice.transcriber import build_transcriber  # noqa: PLC0415

    return build_transcriber()
