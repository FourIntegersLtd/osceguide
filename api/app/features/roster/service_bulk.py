"""Rostering a cohort at once.

Split from `service.py` for size, and because the rule here is its own: an
upload is best-effort per row. One duplicate in a spreadsheet of two hundred
must not refuse the other hundred and ninety-nine, and the administrator has
to be told which rows were skipped and why, rather than left to diff lists.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.roster import errors, service
from app.features.roster.schemas import BulkTraineesResult, CreateTrainee, SkippedTrainee


async def add_trainees(
    session: AsyncSession, org_id: uuid.UUID, *, entries: list[CreateTrainee], now: datetime
) -> BulkTraineesResult:
    """Add every row that can be added; report every row that cannot.

    Each row goes through the same path as a single add, so an unknown address
    is invited and linked exactly as it would be one at a time. Duplicates
    within the upload are skipped after the first, by normalised address, so a
    spreadsheet with the same person twice does not fail on the second.
    """
    result = BulkTraineesResult()
    seen: set[str] = set()
    for entry in entries:
        key = entry.email.strip().lower()
        if key in seen:
            result.skipped.append(SkippedTrainee(email=entry.email, code=errors.TraineeExists.code))
            continue
        seen.add(key)
        try:
            created = await service.add_trainee(
                session,
                org_id,
                email=entry.email,
                first_name=entry.first_name,
                last_name=entry.last_name,
                cohort_id=entry.cohort_id,
                now=now,
            )
        except errors.TraineeExists as exc:
            result.skipped.append(SkippedTrainee(email=entry.email, code=exc.code))
            continue
        result.created.append(created)
    return result
