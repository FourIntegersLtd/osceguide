"""What the account directory knows about access, for many people at once.

`service_platform.py` answers about one person's grants in full; these are
the two questions the directory asks across everybody — who holds a live
grant for an exam, and what each listed person's live access is.
"""

from __future__ import annotations

import uuid
from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog import service as catalog
from app.features.entitlements import repository


@dataclass(frozen=True)
class LiveGrant:
    exam_code: str
    source: str
    ends_at: datetime | None


async def live_user_ids_for_exam(session: AsyncSession, exam_code: str, *, now: datetime) -> set[uuid.UUID]:
    """Everyone entitled to this exam right now. An unknown code is nobody."""
    exam = next((e for e in await catalog.exam_refs(session) if e.code == exam_code), None)
    if exam is None:
        return set()
    return await repository.live_user_ids_for_exam(session, exam.id, now=now)


async def live_grants_by_user(
    session: AsyncSession, user_ids: Collection[uuid.UUID], *, now: datetime
) -> dict[uuid.UUID, list[LiveGrant]]:
    rows = await repository.live_for_users(session, user_ids, now=now)
    codes = await catalog.exam_codes_by_id(session, list({row.exam_id for row in rows}))
    out: dict[uuid.UUID, list[LiveGrant]] = {}
    for row in rows:
        out.setdefault(row.user_id, []).append(
            LiveGrant(exam_code=codes.get(row.exam_id, ""), source=row.source, ends_at=row.ends_at)
        )
    return out
