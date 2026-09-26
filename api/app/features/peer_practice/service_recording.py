"""Recording a peer consultation, and queueing what becomes of it.

Two people practising have no agent in the room keeping a transcript, so the
recording is the only record there will ever be. Start and stop are driven by
the phase machine rather than by a route: the server owns the clock, so no
client can decide — by never calling, or calling twice — whether somebody's
practice gets marked.

**A failed recording never fails a session.** Every path here swallows what it
cannot do, records why on the session, and lets the consultation carry on.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.ports import RoomRecorder
from app.core.settings import Settings, get_settings
from app.features.media_production import service_storage as storage
from app.features.peer_practice import repository_sessions
from app.features.peer_practice.models import PracticeSession
from app.features.voice.errors import VoiceUnavailable

log = get_logger(__name__)


def recording_key(session_id: uuid.UUID, exam_code: str) -> str:
    """Where a session's audio lives. LiveKit writes Ogg for an audio-only egress."""
    return f"peer_practice/{exam_code}/{session_id}/consultation.ogg"


def is_configured(settings: Settings | None = None) -> bool:
    """Whether recording is possible at all. No bucket, no recording."""
    return storage.is_configured(settings or get_settings())


async def start_recording(
    session: AsyncSession,
    practice_session: PracticeSession,
    *,
    exam_code: str,
    recorder: RoomRecorder | None = None,
) -> None:
    """Begin recording the consultation. Idempotent, and never fatal.

    Called as the pair enter the consultation phase — not when they were
    matched, because the preparation phase is somebody reading a brief alone
    and there is nothing to mark in it.
    """
    if practice_session.recording_state != "none" or not practice_session.room_name:
        return
    settings = get_settings()
    if not is_configured(settings):
        # Not an error worth recording on the session: a deployment without a
        # bucket is not a session that went wrong.
        return
    key = recording_key(practice_session.id, exam_code)
    try:
        egress_id = await (recorder or _recorder()).start(room=practice_session.room_name, key=key)
    except VoiceUnavailable as exc:
        log.warning("peer session not recorded", session_id=str(practice_session.id), error=str(exc))
        await repository_sessions.set_recording_state(
            session, practice_session.id, state="failed", error=str(exc)[:200]
        )
        return
    await repository_sessions.set_recording_started(
        session, practice_session.id, egress_id=egress_id, key=key
    )


async def stop_recording_and_queue(
    session: AsyncSession,
    practice_session: PracticeSession,
    *,
    now: datetime,
    mark: bool = True,
    recorder: RoomRecorder | None = None,
) -> None:
    """Stop the recording and queue the transcription, in one transaction.

    `mark=False` still stops the egress (a running one costs money) but queues
    nothing: an abandoned consultation was promised no feedback.

    The job is deferred on this session rather than through procrastinate's own
    connector, so the row saying "stopped" and the work that reads it commit
    together (ADR 0006). Deferring on the other connection would let the job
    run against a state that then rolled back — and the recording it was told
    to fetch would be one nothing had stopped.
    """
    from app.features.peer_practice.jobs import enqueue_transcription  # noqa: PLC0415

    if practice_session.recording_state != "recording" or not practice_session.egress_id:
        return
    try:
        await (recorder or _recorder()).stop(egress_id=practice_session.egress_id)
    except VoiceUnavailable as exc:
        # The audio may still have been written — egress uploads what it has —
        # so this is worth transcribing anyway rather than abandoning.
        log.warning("peer recording not stopped cleanly", session_id=str(practice_session.id), error=str(exc))
    await repository_sessions.set_recording_state(session, practice_session.id, state="stopped")
    if not mark:
        return
    await enqueue_transcription(session, session_id=practice_session.id, now=now)


def _recorder() -> RoomRecorder:
    """Built here rather than injected through the router.

    Both callers are the phase machine, which is reached from a heartbeat and
    from a job as well as from a route, so there is no one place a dependency
    could be wired. A test passes its own `recorder` instead.
    """
    from app.features.voice import service as voice

    return voice.get_room_recorder()
