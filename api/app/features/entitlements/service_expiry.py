"""The warning, a week ahead, that bought access is about to end (S-12).

Checkout refuses a second purchase while the first is live (A-24), so the honest
message is the end date and where to buy again afterwards; it does not promise a
renewal that the person cannot yet make.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog import service as catalog
from app.features.entitlements import repository
from app.features.identity import service as identity
from app.features.notifications import service as notifications

WARN_DAYS = 7


async def warn_expiring_access(session: AsyncSession, *, now: datetime) -> int:
    """Queue one email per purchase ending within `WARN_DAYS`; returns how many were queued.

    Idempotent on the entitlement, so the hourly job and an overlapping worker send one.
    Skipped when the person already holds bought access for the same exam that outlasts this one.
    """
    queued = 0
    for grant in await repository.purchases_ending_between(
        session, after=now, before=now + timedelta(days=WARN_DAYS)
    ):
        ends_at = grant.ends_at
        if ends_at is None:
            continue
        held = await repository.for_user_and_exam(session, grant.user_id, grant.exam_id)
        if any(
            other.id != grant.id
            and other.source == "purchase"
            and other.revoked_at is None
            and other.ends_at is not None
            and other.ends_at > ends_at
            for other in held
        ):
            continue
        person = await identity.user_ref_by_id(session, grant.user_id)
        exam = await catalog.exam_ref_by_id(session, grant.exam_id)
        if person is None or exam is None:
            continue
        sent = await notifications.enqueue_email(
            session,
            recipient=person.email,
            subject=f"Your {exam.name} access ends on {ends_at:%-d %B %Y}",
            template_key="entitlement_expiring",
            payload={"exam_title": exam.name, "ends_on": f"{ends_at:%-d %B %Y}"},
            idempotency_key=f"entitlement_expiring:{grant.id}",
        )
        queued += int(sent)
    return queued
