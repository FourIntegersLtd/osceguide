"""Storage for exams and org programmes."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import encode_cursor
from app.features.catalog.models import Exam, Programme


async def list_exams(session: AsyncSession) -> list[Exam]:
    """All four, unpaged: the set is closed and small by design."""
    return list((await session.execute(select(Exam).order_by(Exam.code))).scalars())


async def exam_by_code(session: AsyncSession, code: str) -> Exam | None:
    stmt = select(Exam).where(Exam.code == code.strip().lower())
    return (await session.execute(stmt)).scalar_one_or_none()


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
    stmt = select(Programme, Exam).join(Exam, Exam.id == Programme.exam_id).where(Programme.org_id == org_id)
    if cursor:
        stmt = stmt.where(Programme.created_at > datetime.fromisoformat(cursor["t"]))
    rows = list(
        (await session.execute(stmt.order_by(Programme.created_at, Programme.id).limit(limit + 1))).all()
    )
    pairs = [(r[0], r[1]) for r in rows]
    if len(pairs) <= limit:
        return pairs, None
    page = pairs[:limit]
    return page, encode_cursor({"t": page[-1][0].created_at, "i": str(page[-1][0].id)})


async def set_programme_status(
    session: AsyncSession, org_id: uuid.UUID, programme_id: uuid.UUID, *, status: str
) -> None:
    await session.execute(
        update(Programme)
        .where(Programme.org_id == org_id, Programme.id == programme_id)
        .values(status=status)
    )
