"""The worker tasks that erase closed accounts (E-4) and nudge inactive ones."""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.jobs import get_jobs_app
from app.core.logging import get_logger
from app.core.settings import get_settings

log = get_logger(__name__)


def register() -> None:
    """Wire the erasure and engagement-email tasks into the shared jobs app,
    each on its own daily schedule."""
    app = get_jobs_app()

    @app.periodic(cron="0 3 * * *")
    @app.task(name="erase_closed_accounts", queue="identity")
    async def erase_closed_accounts(timestamp: int = 0) -> None:
        """Run once a day: scrub every account closed 30+ days ago that has
        not already been erased."""
        from app.core.db import job_session
        from app.features.identity.service_erasure import erase_due_accounts

        erased = await erase_due_accounts(job_session, now=datetime.now(UTC))
        if erased:
            log.info("accounts erased", count=erased)

    @app.periodic(cron="0 9 * * *")
    @app.task(name="send_engagement_emails", queue="identity")
    async def send_engagement_emails(timestamp: int = 0) -> None:
        """Run once a day: queue the "come try a station" nudge for every
        eligible account. A no-op while `ENGAGEMENT_EMAIL_ENABLED` is unset —
        see `docs/ENVIRONMENT.md` — so a freshly deployed environment cannot
        fire this on real inboxes until the owner switches it on."""
        if not get_settings().engagement_email_enabled:
            return
        from app.core.db import job_session
        from app.features.identity.service_engagement import send_due_engagement_emails

        async with job_session() as session:
            sent = await send_due_engagement_emails(session, now=datetime.now(UTC))
            if sent:
                log.info("engagement emails queued", count=sent)

    @app.periodic(cron="0 10 * * *")
    @app.task(name="send_invitation_reminders", queue="identity")
    async def send_invitation_reminders(timestamp: int = 0) -> None:
        """Run once a day: remind every invitee who has not answered after five days."""
        from app.core.db import job_session
        from app.features.identity.service_invitations import send_due_invitation_reminders

        async with job_session() as session:
            reminded = await send_due_invitation_reminders(session, now=datetime.now(UTC))
            if reminded:
                log.info("invitation reminders queued", count=reminded)
