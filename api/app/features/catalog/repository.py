"""Storage for exams and org programmes."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import keyset_page
from app.features.catalog.models import Exam, Programme


async def list_exams(session: AsyncSession, *, statuses: Sequence[str] | None = None) -> list[Exam]:
    """Every exam, or only those in the given states. Unpaged: the set is small.

    `statuses=None` is the platform admin's view, which includes drafts.
    """
    stmt = select(Exam).order_by(Exam.code)
    if statuses is not None:
        stmt = stmt.where(Exam.status.in_(list(statuses)))
    return list((await session.execute(stmt)).scalars())


async def exam_by_code(session: AsyncSession, code: str) -> Exam | None:
    stmt = select(Exam).where(Exam.code == code.strip().lower())
    return (await session.execute(stmt)).scalar_one_or_none()


async def create_exam(
    session: AsyncSession,
    *,
    code: str,
    name: str,
    default_reading_seconds: int,
    default_simulation_seconds: int,
    station_attempt_limit: int,
    rubric_version_id: uuid.UUID | None,
    partner_pilot: bool,
) -> Exam:
    exam = Exam(
        code=code,
        name=name,
        default_reading_seconds=default_reading_seconds,
        default_simulation_seconds=default_simulation_seconds,
        station_attempt_limit=station_attempt_limit,
        rubric_version_id=rubric_version_id,
        partner_pilot=partner_pilot,
    )
    session.add(exam)
    await session.flush()
    await session.refresh(exam)
    return exam


async def update_exam(session: AsyncSession, exam_id: uuid.UUID, **fields: Any) -> None:
    if fields:
        await session.execute(update(Exam).where(Exam.id == exam_id).values(**fields))


async def pilot_exam_codes(session: AsyncSession) -> list[str]:
    """Exams a partner attribution link may name. Was a tuple in `growth.domain`."""
    stmt = select(Exam.code).where(Exam.partner_pilot.is_(True)).order_by(Exam.code)
    return [row for row in (await session.execute(stmt)).scalars()]


async def exam_by_id(session: AsyncSession, exam_id: uuid.UUID) -> Exam | None:
    return (await session.execute(select(Exam).where(Exam.id == exam_id))).scalar_one_or_none()


async def create_programme(
    session: AsyncSession, org_id: uuid.UUID, *, exam_id: uuid.UUID, source: str = "custom"
) -> Programme:
    programme = Programme(org_id=org_id, exam_id=exam_id, source=source)
    session.add(programme)
    await session.flush()
    await session.refresh(programme)
    return programme


async def programme_for_exam(
    session: AsyncSession, org_id: uuid.UUID, exam_id: uuid.UUID
) -> Programme | None:
    stmt = select(Programme).where(Programme.org_id == org_id, Programme.exam_id == exam_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def programme_by_id(
    session: AsyncSession, org_id: uuid.UUID, programme_id: uuid.UUID
) -> Programme | None:
    stmt = select(Programme).where(Programme.org_id == org_id, Programme.id == programme_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_programmes(
    session: AsyncSession, org_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None = None
) -> tuple[list[tuple[Programme, Exam]], str | None]:
    stmt = select(Programme).where(Programme.org_id == org_id)
    programmes, next_cursor = await keyset_page(
        session,
        stmt,
        sort_col=Programme.created_at,
        id_col=Programme.id,
        limit=limit,
        cursor=cursor,
        descending=False,
    )
    exam_ids = {p.exam_id for p in programmes}
    exams = {e.id: e for e in (await session.execute(select(Exam).where(Exam.id.in_(exam_ids)))).scalars()}
    return [(p, exams[p.exam_id]) for p in programmes], next_cursor


async def set_programme_status(
    session: AsyncSession, org_id: uuid.UUID, programme_id: uuid.UUID, *, status: str
) -> None:
    await session.execute(
        update(Programme)
        .where(Programme.org_id == org_id, Programme.id == programme_id)
        .values(status=status)
    )


async def exams_by_ids(session: AsyncSession, exam_ids: Sequence[uuid.UUID]) -> list[Exam]:
    if not exam_ids:
        return []
    stmt = select(Exam).where(Exam.id.in_(list(exam_ids)))
    return list((await session.execute(stmt)).scalars())
