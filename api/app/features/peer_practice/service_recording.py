"""Recording a peer consultation, and queueing what becomes of it.

Two people practising have no agent in the room, so nothing is keeping a
transcript the way an attempt's patient worker does. The recording is the only
record there will ever be, and the marking is built from it afterwards — which
is why the whole of P-1 hangs off these two moments.

Both are driven by the phase machine rather than by a route. b2c's client
called `start-egress` and `consultation-ended` itself; here the server already
owns the clock, so a client that never called them, or called them twice,
cannot decide whether somebody's practice is marked.

**A failed recording never fails a session.** Every path here swallows what it
cannot do, records why on the row, and lets the consultation carry on. The
practice is worth more than the recording of it.
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
    row: PracticeSession,
    *,
    exam_code: str,
    recorder: RoomRecorder | None = None,
) -> None:
    """Begin recording the consultation. Idempotent, and never fatal.

    Called as the pair enter the consultation phase — not when they were
    matched, because the preparation phase is somebody reading a brief alone
    and there is nothing to mark in it.
    """
    if row.recording_state != "none" or not row.room_name:
        return
    settings = get_settings()
    if not is_configured(settings):
        # Not an error worth recording on the row: a deployment without a
        # bucket is not a session that went wrong.
        return
    key = recording_key(row.id, exam_code)
    try:
        egress_id = await (recorder or _recorder()).start(room=row.room_name, key=key)
    except VoiceUnavailable as exc:
        log.warning("peer session not recorded", session_id=str(row.id), error=str(exc))
        await repository_sessions.set_recording_state(session, row.id, state="failed", error=str(exc)[:200])
        return
    await repository_sessions.set_recording_started(session, row.id, egress_id=egress_id, key=key)


async def stop_recording_and_queue(
    session: AsyncSession,
    row: PracticeSession,
    *,
    now: datetime,
    recorder: RoomRecorder | None = None,
) -> None:
    """Stop the recording and queue the transcription, in one transaction.

    The job is deferred on this session rather than through procrastinate's own
    connector, so the row saying "stopped" and the work that reads it commit
    together (ADR 0006). Deferring on the other connection would let the job
    run against a state that then rolled back — and the recording it was told
    to fetch would be one nothing had stopped.
    """
    from app.features.peer_practice.jobs import enqueue_transcription  # noqa: PLC0415

    if row.recording_state != "recording" or not row.egress_id:
        return
    try:
        await (recorder or _recorder()).stop(egress_id=row.egress_id)
    except VoiceUnavailable as exc:
        # The audio may still have been written — egress uploads what it has —
        # so this is worth transcribing anyway rather than abandoning.
        log.warning("peer recording not stopped cleanly", session_id=str(row.id), error=str(exc))
    await repository_sessions.set_recording_state(session, row.id, state="stopped")
    await enqueue_transcription(session, session_id=row.id, now=now)


def _recorder() -> RoomRecorder:
    """Built here rather than injected through the router.

    Both callers are the phase machine, which is reached from a heartbeat and
    from a job as well as from a route, so there is no one place a dependency
    could be wired. A test passes its own `recorder` instead.
    """
    from app.features.voice import service_recording as voice  # noqa: PLC0415

    return voice.get_room_recorder()
