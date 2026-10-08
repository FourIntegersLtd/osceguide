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
    Skipped when other live access to the same exam outlasts this one, and for a plan no longer
    than the warning itself (it would be warned within the hour of buying).
    """
    queued = 0
    warning = timedelta(days=WARN_DAYS)
    for grant in await repository.purchases_ending_between(session, after=now, before=now + warning):
        ends_at = grant.ends_at
        if ends_at is None:
            continue
        if grant.starts_at >= ends_at - warning or await repository.has_later_access(session, grant, now=now):
            continue
        person = await identity.user_ref_by_id(session, grant.user_id)
        exam = await catalog.exam_ref_by_id(session, grant.exam_id)
        if person is None or exam is None:
            continue
        ends_on = f"{ends_at:%-d %B %Y}"
        sent = await notifications.enqueue_email(
            session,
            recipient=person.email,
            subject=f"Your {exam.name} access ends on {ends_on}",
            template_key="entitlement_expiring",
            payload={"exam_title": exam.name, "ends_on": ends_on},
            idempotency_key=f"entitlement_expiring:{grant.id}",
        )
        queued += int(sent)
    return queued
