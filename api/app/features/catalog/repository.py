"""Storage for exams and org programmes."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ownership import visible_to
from app.core.pagination import keyset_page
from app.features.catalog.domain import ExamStatus
from app.features.catalog.models import Exam, Programme


async def list_exams(
    session: AsyncSession,
    org_id: uuid.UUID | None = None,
    *,
    statuses: Sequence[str] | None = None,
    owned_only: bool = False,
) -> list[Exam]:
    """Exams this caller may see. Unpaged: the set is small.

    `statuses=None` is the owner's own view, which includes drafts.
    `owned_only` narrows to rows this caller wrote, which is what a draft
    listing means: an institution's drafts are its own business, and so are
    ours. Otherwise an org sees its own exams plus the platform catalogue,
    and the platform sees only its own — the library is shared downward,
    never an institution's content upward.
    """
    stmt = select(Exam).order_by(Exam.code)
    stmt = stmt.where(Exam.org_id == org_id) if owned_only else stmt.where(visible_to(Exam, org_id))
    if statuses is not None:
        stmt = stmt.where(Exam.status.in_(list(statuses)))
    return list((await session.execute(stmt)).scalars())


async def exam_by_code(session: AsyncSession, org_id: uuid.UUID | None, code: str) -> Exam | None:
    """One exam by code, within what this caller may see.

    A code is unique per owner, so an org that has written its own `plab` gets
    that one and not the platform's: an institution's own exam wins its own
    namespace. Ordered so the answer does not depend on insertion order.
    """
    stmt = (
        select(Exam)
        .where(visible_to(Exam, org_id), Exam.code == code.strip().lower())
        .order_by(Exam.org_id.is_(None))
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def owned_exam_by_code(session: AsyncSession, org_id: uuid.UUID | None, code: str) -> Exam | None:
    """One exam by code in this owner's own namespace, for a uniqueness check."""
    stmt = select(Exam).where(Exam.org_id == org_id, Exam.code == code.strip().lower())
    return (await session.execute(stmt)).scalar_one_or_none()


async def create_exam(
    session: AsyncSession,
    *,
    owner_kind: str,
    org_id: uuid.UUID | None,
    code: str,
    name: str,
    default_reading_seconds: int,
    default_simulation_seconds: int,
    station_attempt_limit: int,
    rubric_version_id: uuid.UUID | None,
    partner_pilot: bool,
) -> Exam:
    exam = Exam(
        owner_kind=owner_kind,
        org_id=org_id,
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
    """Exams a partner attribution link may name. Was a tuple in `growth.domain`.

    Consumer-side, so platform exams only: a partner link is a B2C funnel and
    can never name an institution's private exam.
    """
    stmt = select(Exam.code).where(Exam.partner_pilot.is_(True), Exam.org_id.is_(None)).order_by(Exam.code)
    return [row for row in (await session.execute(stmt)).scalars()]


async def exam_by_id(session: AsyncSession, exam_id: uuid.UUID) -> Exam | None:
    """One exam by id, with no visibility filter.

    By id and unscoped deliberately: an attempt sat last year has to render
    whoever owns the exam it named. The callers that must not cross an owner
    boundary check ownership themselves, in the service.
    """
    return (await session.execute(select(Exam).where(Exam.id == exam_id))).scalar_one_or_none()


async def exam_code_by_id(session: AsyncSession, exam_id: uuid.UUID) -> str | None:
    """Exam code only — works when older DB rows lack `exams.framework_id`."""
    row = await session.execute(select(Exam.code).where(Exam.id == exam_id))
    return row.scalar_one_or_none()


async def exam_codes_by_id(session: AsyncSession, exam_ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    """Batch lookup for list endpoints that would otherwise N+1 the exams table."""
    if not exam_ids:
        return {}
    rows = await session.execute(select(Exam.id, Exam.code).where(Exam.id.in_(exam_ids)))
    return {row[0]: str(row[1]) for row in rows.all()}


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


async def count_programmes_with_markable_exam(session: AsyncSession, org_id: uuid.UUID) -> int:
    """Programmes whose exam is published and names a rubric version."""
    stmt = (
        select(func.count())
        .select_from(Programme)
        .join(Exam, Exam.id == Programme.exam_id)
        .where(
            Programme.org_id == org_id,
            Exam.status == ExamStatus.PUBLISHED,
            Exam.rubric_version_id.isnot(None),
        )
    )
    return int((await session.execute(stmt)).scalar_one())
