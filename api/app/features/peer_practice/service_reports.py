"""Safety reports: abuse and no-show, emailed to support rather than only logged."""

from __future__ import annotations

import hashlib
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.features.identity import service as identity
from app.features.notifications import service as notifications
from app.features.peer_practice import errors, repository_sessions


def _digest(message: str | None) -> str:
    """What makes a report the same report: a resubmitted form deduplicates, a new message does not."""
    return hashlib.sha256((message or "").strip().encode()).hexdigest()[:16]


async def report_abuse(
    session: AsyncSession, session_id: uuid.UUID, *, reporter_id: uuid.UUID, message: str | None
) -> None:
    """A safety report, emailed to support rather than only logged.

    A report that only reaches the server log is one nobody reads until
    somebody goes looking, which is not what "report" means to the person
    who filed it.
    """
    practice_session = await repository_sessions.session_by_id(session, session_id)
    if practice_session is None or reporter_id not in {
        practice_session.doctor_user_id,
        practice_session.patient_user_id,
    }:
        raise errors.SessionNotFound()
    reported_id = (
        practice_session.patient_user_id
        if reporter_id == practice_session.doctor_user_id
        else practice_session.doctor_user_id
    )
    refs = await identity.user_refs_by_ids(session, [reporter_id, reported_id])
    reporter_ref = refs.get(reporter_id)
    reported_ref = refs.get(reported_id)
    await notifications.enqueue_email(
        session,
        recipient=get_settings().support_email,
        subject="Peer-practice abuse report",
        template_key="peer_practice_abuse_report",
        payload={
            "session_id": str(session_id),
            "reporter": reporter_ref.email if reporter_ref else str(reporter_id),
            "reported": reported_ref.email if reported_ref else str(reported_id),
            "message": message or "",
        },
        idempotency_key=f"peer_practice_abuse_report:{session_id}:{reporter_id}:{_digest(message)}",
    )


async def report_no_show(
    session: AsyncSession, session_id: uuid.UUID, *, reporter_id: uuid.UUID, message: str | None
) -> None:
    """A report that the other participant never turned up, emailed to support."""
    practice_session = await repository_sessions.session_by_id(session, session_id)
    if practice_session is None or reporter_id not in {
        practice_session.doctor_user_id,
        practice_session.patient_user_id,
    }:
        raise errors.SessionNotFound()
    refs = await identity.user_refs_by_ids(session, [reporter_id])
    reporter_ref = refs.get(reporter_id)
    await notifications.enqueue_email(
        session,
        recipient=get_settings().support_email,
        subject="Peer-practice no-show report",
        template_key="peer_practice_no_show_report",
        payload={
            "session_id": str(session_id),
            "reporter": reporter_ref.email if reporter_ref else str(reporter_id),
            "message": message or "",
        },
        idempotency_key=f"peer_practice_no_show_report:{session_id}:{reporter_id}:{_digest(message)}",
    )
