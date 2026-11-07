"""Removing candidates' transcripts: on an organisation's retention schedule, or when staff ask.

Only what a person said is removed. The attempt, its marks and the organisation's result
history stay, so a sitting's report and the result ledger still add up.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionOpener
from app.features.attempts import repository, repository_transcript
from app.features.tenancy import service as tenancy

RETENTION_BATCH = 200


class RetentionFailed(Exception):
    """Some organisations could not be swept. The others were; the next run tries these again."""


async def erase_for_user_in_org(
    session: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, *, now: datetime
) -> int:
    """Remove every transcript this person left inside one organisation. Answers how many attempts."""
    attempt_ids = await repository.attempt_ids_for_user_in_org(session, org_id, user_id)
    await repository_transcript.erase_transcripts_for_attempts(session, attempt_ids)
    await repository.mark_content_erased(session, attempt_ids, at=now)
    return len(attempt_ids)


async def sweep_retention(open_session: SessionOpener, *, now: datetime) -> int:
    """Remove the transcripts that have outlived their organisation's retention. Answers how many attempts.

    One transaction per organisation, so one failure rolls back only itself; failures are
    collected and raised once the rest are done, so the queue row shows the run failed.
    """
    async with open_session() as session:
        policies = await tenancy.retention_policies(session)
    erased = 0
    failed: list[uuid.UUID] = []
    first_error: Exception | None = None
    for org_id, days in policies.items():
        try:
            async with open_session() as session:
                ids = await repository.attempt_ids_past_retention(
                    session, org_id, cutoff=now - timedelta(days=days), limit=RETENTION_BATCH
                )
                await repository_transcript.erase_transcripts_for_attempts(session, ids)
                await repository.mark_content_erased(session, ids, at=now)
                erased += len(ids)
        except Exception as error:  # noqa: BLE001 - collected, and raised once the rest are done
            failed.append(org_id)
            first_error = first_error or error
    if failed:
        raise RetentionFailed(
            f"Retention failed for {len(failed)} of {len(policies)} organisations: {failed}"
        ) from first_error
    return erased
