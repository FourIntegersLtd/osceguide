"""Folding a finished transcript's rows into one document (see `repository_transcript.compact`)."""

from __future__ import annotations

import uuid

from app.core.db import SessionOpener
from app.features.attempts import repository_transcript as transcripts


class CompactionFailed(Exception):
    """Some attempts could not be compacted. The others were; the next run tries these again."""


async def compact_ready_transcripts(open_session: SessionOpener, *, limit: int) -> int:
    """Compact up to `limit` ready transcripts and answer how many changed.

    Each attempt gets a transaction of its own, so one failure rolls back only itself. Failures
    are collected and raised once the rest are done, so the queue row shows the run failed.
    """
    async with open_session() as session:
        ready = await transcripts.attempt_ids_ready_to_compact(session, limit=limit)
    compacted = 0
    failed: list[uuid.UUID] = []
    first_error: Exception | None = None
    for attempt_id in ready:
        try:
            async with open_session() as session:
                if await transcripts.compact(session, attempt_id):
                    compacted += 1
        except Exception as error:  # noqa: BLE001 - collected, and raised once the rest are done
            failed.append(attempt_id)
            first_error = first_error or error
    if failed:
        message = f"{len(failed)} of {len(ready)} transcripts failed to compact: {failed}"
        raise CompactionFailed(message) from first_error
    return compacted
