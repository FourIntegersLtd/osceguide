"""A person's attempts as the console sees them by station, and the two
things the old console could do to them.

The B2C admin kept a `station_progress` array per user with an attempt counter
per station, a "reset attempts" button that zeroed the counter, and a "delete
station" button that took the transcripts and feedback with it. On the
platform the counter lives on a practice set's entry — `station_sets` owns
that — and the record of what happened is here. So this module answers the
attempt half: how many, how many marked, when last, and the delete. The
counters and the audit row are the caller's, one layer up.
"""

from __future__ import annotations

import uuid
from collections.abc import Collection

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import errors, repository_platform
from app.features.attempts.repository_platform import VersionProgress
from app.features.identity import service as identity


async def attempted_user_ids(session: AsyncSession) -> set[uuid.UUID]:
    """Everyone who has started at least one attempt."""
    return await repository_platform.attempted_user_ids(session)


async def attempt_counts(session: AsyncSession, user_ids: Collection[uuid.UUID]) -> dict[uuid.UUID, int]:
    return await repository_platform.count_by_user(session, user_ids)


async def progress_by_version(session: AsyncSession, user_id: uuid.UUID) -> list[VersionProgress]:
    """One row per station version this person has sat, newest first."""
    if await identity.user_ref_by_id(session, user_id) is None:
        raise errors.UserNotFound()
    return await repository_platform.progress_by_version(session, user_id)


async def delete_progress(
    session: AsyncSession, user_id: uuid.UUID, version_ids: Collection[uuid.UUID]
) -> int:
    """Erase this person's attempts at these versions. Refused while one is
    still running: a consultation in progress would lose its room from under
    it, and the worker would write turns against a row that no longer exists.
    """
    if await identity.user_ref_by_id(session, user_id) is None:
        raise errors.UserNotFound()
    if await repository_platform.running_for_user_versions(session, user_id, version_ids):
        raise errors.AttemptInProgress()
    return await repository_platform.delete_for_user_versions(session, user_id, version_ids)
