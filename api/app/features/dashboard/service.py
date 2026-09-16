"""Assembling the learner's dashboard.

Reads through other slices' services rather than their tables, so this stays a
projection and cannot quietly become a second owner of anyone's data.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import repository as attempts_repo
from app.features.attempts import repository_transcript as transcripts_repo
from app.features.catalog import repository as catalog_repo
from app.features.dashboard.schemas import (
    Dashboard,
    EntitlementSummary,
    ExamProgress,
    RecentAttempt,
    SetSummary,
)
from app.features.entitlements import service as entitlements
from app.features.station_sets import service as station_sets

RECENT_LIMIT = 10


async def build(session: AsyncSession, user_id: uuid.UUID, *, now: datetime) -> Dashboard:
    grants = await entitlements.list_for_user(session, user_id, now=now)
    sets, _ = await station_sets.list_sets(session, user_id, limit=RECENT_LIMIT, cursor=None)
    attempts, _ = await attempts_repo.list_for_user(session, user_id, limit=RECENT_LIMIT)

    exam_codes: dict[uuid.UUID, str] = {}
    recent: list[RecentAttempt] = []
    progress: dict[str, ExamProgress] = {}

    for attempt in attempts:
        if attempt.exam_id not in exam_codes:
            exam = await catalog_repo.exam_by_id(session, attempt.exam_id)
            exam_codes[attempt.exam_id] = exam.code if exam else ""
        code = exam_codes[attempt.exam_id]

        results = await transcripts_repo.results_for(session, attempt.id)
        recent.append(
            RecentAttempt(
                id=attempt.id,
                kind=attempt.kind,
                status=attempt.status,
                exam_code=code,
                created_at=attempt.created_at,
                has_result=bool(results),
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

    return Dashboard(
        user_id=user_id,
        entitlements=[
            EntitlementSummary(exam_code=g.exam_code, source=g.source, ends_at=g.ends_at, live=g.live)
            for g in grants
        ],
        progress=sorted(progress.values(), key=lambda p: p.exam_code),
        recent_attempts=recent,
        sets=[
            SetSummary(
                id=s.id,
                name=s.name,
                exam_code=s.exam_code,
                attempted_entries=s.attempted_entries,
                total_entries=s.total_entries,
                locked=s.locked,
            )
            for s in sets
        ],
    )
