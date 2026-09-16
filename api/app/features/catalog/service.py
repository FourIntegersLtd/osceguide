"""Catalog use cases."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog import domain, repository
from app.features.catalog.errors import ProgrammeExists, ProgrammeNotFound, UnknownExamError
from app.features.catalog.models import Exam, Programme
from app.features.catalog.schemas import ExamRead, ProgrammeRead


async def list_exams(session: AsyncSession) -> list[ExamRead]:
    return [_exam_read(e) for e in await repository.list_exams(session)]


async def resolve_exam(session: AsyncSession, code: str) -> Exam:
    """Look an exam up by code, refusing anything unknown.

    Never defaulted. b2c fell back to `sca` for an unrecognised `app_type`,
    which is how CASC transcripts came to be marked with a GP rubric prompt.
    """
    try:
        domain.exam_by_code(code)
    except domain.UnknownExam as exc:
        raise UnknownExamError(str(exc)) from exc
    exam = await repository.exam_by_code(session, code)
    if exam is None:
        # The domain knows this exam but the table does not: the seed migration
        # and the code have diverged, which is a deployment fault, not a client one.
        raise UnknownExamError(f"Exam {code!r} is published but not seeded")
    return exam


async def add_programme(session: AsyncSession, org_id: uuid.UUID, *, exam_code: str) -> ProgrammeRead:
    exam = await resolve_exam(session, exam_code)
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


def _exam_read(exam: Exam) -> ExamRead:
    return ExamRead(
        id=exam.id,
        code=exam.code,
        name=exam.name,
        framework_id=exam.framework_id,
        default_reading_seconds=exam.default_reading_seconds,
        default_simulation_seconds=exam.default_simulation_seconds,
        station_attempt_limit=exam.station_attempt_limit,
    )


def _programme_read(programme: Programme, exam: Exam) -> ProgrammeRead:
    return ProgrammeRead(
        id=programme.id,
        exam_id=exam.id,
        exam_code=exam.code,
        exam_name=exam.name,
        status=programme.status,
        source=programme.source,
    )


async def exam_for_attempt(session: AsyncSession, exam_id: uuid.UUID) -> Exam:
    """The exam row an attempt was created against.

    Returns the row rather than a field, because rendering needs its code, its
    framework and its marking model together and there is no reason to read it
    three times.
    """
    exam = await repository.exam_by_id(session, exam_id)
    if exam is None:
        raise UnknownExamError(f"No exam with id {exam_id}.")
    return exam
