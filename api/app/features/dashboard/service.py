"""Assembling the learner's dashboard.

Reads through other slices' services rather than their tables, so this stays a
projection and cannot quietly become a second owner of anyone's data.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import service_reads as attempts_reads
from app.features.catalog import service as catalog
from app.features.dashboard.schemas import (
    Dashboard,
    EntitlementSummary,
    ExamProgress,
    RecentAttempt,
    SetSummary,
)
from app.features.entitlements import service as entitlements
from app.features.entitlements import service_access as entitlement_access
from app.features.station_sets import service as station_sets

RECENT_LIMIT = 10


async def build(session: AsyncSession, user_id: uuid.UUID, *, now: datetime) -> Dashboard:
    grants = await entitlements.list_for_user(session, user_id, now=now)
    sets, _ = await station_sets.list_sets(session, user_id, limit=RECENT_LIMIT, cursor=None)
    attempts = await attempts_reads.recent_for_user(session, user_id, limit=RECENT_LIMIT)

    exam_codes: dict[uuid.UUID, str] = {}
    recent: list[RecentAttempt] = []
    progress: dict[str, ExamProgress] = {}

    for attempt in attempts:
        if attempt.exam_id not in exam_codes:
            exam_codes[attempt.exam_id] = await catalog.exam_code_by_id(session, attempt.exam_id) or ""
        code = exam_codes[attempt.exam_id]

        recent.append(
            RecentAttempt(
                id=attempt.id,
                kind=attempt.kind,
                status=attempt.status,
                exam_code=code,
                created_at=attempt.created_at,
                has_result=attempt.has_result,
            )
        )

        current = progress.get(
            code, ExamProgress(exam_code=code, attempts=0, evaluated=0, last_attempt_at=None)
        )
        progress[code] = ExamProgress(
            exam_code=code,
            attempts=current.attempts + 1,
            evaluated=current.evaluated + (1 if attempt.status == "evaluated" else 0),
            last_attempt_at=max(filter(None, [current.last_attempt_at, attempt.created_at]), default=None),
        )

    # Which exams this person may open. The rule is `entitlements`' own, and
    # three screens ask it — this one, the station library and the study
    # library — so it is asked through that slice's service rather than
    # rebuilt here.
    access = await entitlement_access.exam_access_for(session, user_id, now=now)

    return Dashboard(
        user_id=user_id,
        exam_codes=list(access.codes),
        current_exam_code=access.current,
        entitlements=[
            EntitlementSummary(
                exam_code=grant.exam_code, source=grant.source, ends_at=grant.ends_at, live=grant.live
            )
            for grant in grants
        ],
        progress=sorted(progress.values(), key=lambda exam_progress: exam_progress.exam_code),
        recent_attempts=recent,
        sets=[
            SetSummary(
                id=station_set.id,
                name=station_set.name,
                exam_code=station_set.exam_code,
                attempted_entries=station_set.attempted_entries,
                total_entries=station_set.total_entries,
                locked=station_set.locked,
            )
            for station_set in sets
        ],
    )
