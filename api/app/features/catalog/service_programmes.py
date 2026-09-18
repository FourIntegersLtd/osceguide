"""One organisation offering one exam.

Split from `service.py` along the two concepts ADR 0011 keeps apart: that
module publishes exams, this one records who runs them. A programme may only
name an exam that is actually being offered, which `resolve_exam` enforces.

The exam it names is the institution's own or one the platform published — both
resolve through the same call, scoped to the org, so a school never has to pick
from a list we happen to have written.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog import repository
from app.features.catalog.errors import ProgrammeExists, ProgrammeNotFound
from app.features.catalog.models import Exam, Programme
from app.features.catalog.schemas import ProgrammeRead
from app.features.catalog.service import resolve_exam


async def add_programme(session: AsyncSession, org_id: uuid.UUID, *, exam_code: str) -> ProgrammeRead:
    exam = await resolve_exam(session, exam_code, org_id=org_id)
    if await repository.programme_for_exam(session, org_id, exam.id) is not None:
        raise ProgrammeExists()
    programme = await repository.create_programme(session, org_id, exam_id=exam.id)
    return _programme_read(programme, exam)


async def list_programmes(
    session: AsyncSession, org_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None
) -> tuple[list[ProgrammeRead], str | None]:
    pairs, next_cursor = await repository.list_programmes(session, org_id, limit=limit, cursor=cursor)
    return [_programme_read(p, e) for p, e in pairs], next_cursor


async def set_programme_status(
    session: AsyncSession, org_id: uuid.UUID, programme_id: uuid.UUID, *, status: str
) -> ProgrammeRead:
    programme = await repository.programme_by_id(session, org_id, programme_id)
    if programme is None:
        raise ProgrammeNotFound()
    await repository.set_programme_status(session, org_id, programme_id, status=status)
    refreshed = await repository.programme_by_id(session, org_id, programme_id)
    exam = await repository.exam_by_id(session, refreshed.exam_id)  # type: ignore[union-attr]
    return _programme_read(refreshed, exam)  # type: ignore[arg-type]


def _programme_read(programme: Programme, exam: Exam) -> ProgrammeRead:
    return ProgrammeRead(
        id=programme.id,
        exam_id=exam.id,
        exam_code=exam.code,
        exam_name=exam.name,
        exam_owner_kind=exam.owner_kind,
        status=programme.status,
        source=programme.source,
    )
