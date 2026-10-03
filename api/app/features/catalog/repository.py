"""Storage for exams and org programmes."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ownership import visible_to
from app.core.pagination import keyset_page
from app.core.search import contains_text
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

    `owned_only` narrows to rows this caller wrote — an institution's drafts
    are its own business, and so are ours. Otherwise an org sees its own exams
    plus the platform catalogue, and the platform sees only its own.
    """
    stmt = select(Exam).order_by(Exam.code)
    stmt = stmt.where(Exam.org_id == org_id) if owned_only else stmt.where(visible_to(Exam, org_id))
    if statuses is not None:
        stmt = stmt.where(Exam.status.in_(list(statuses)))
    return list((await session.execute(stmt)).scalars())


async def list_platform_exams(
    session: AsyncSession, *, status: str | None, limit: int, cursor: dict[str, Any] | None = None
) -> tuple[list[Exam], str | None]:
    """A page of the platform's own exams, every status, oldest first.

    Not org-scoped: this is the console's list of the consumer catalogue, and
    an institution's own exams never appear in it.
    """
    stmt = select(Exam).where(Exam.org_id.is_(None))
    if status is not None:
        stmt = stmt.where(Exam.status == status)
    return await keyset_page(
        session,
        stmt,
        sort_col=Exam.created_at,
        id_col=Exam.id,
        limit=limit,
        cursor=cursor,
        descending=False,
    )


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
    settings: dict[str, Any],
) -> Exam:
    """Insert a new exam row as a draft, and hand back the row with its id set."""
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
        settings=settings,
    )
    session.add(exam)
    await session.flush()
    await session.refresh(exam)
    return exam


async def update_exam(session: AsyncSession, exam_id: uuid.UUID, **fields: Any) -> None:
    """Change whichever columns are given. Does nothing if `fields` is empty."""
    if fields:
        await session.execute(update(Exam).where(Exam.id == exam_id).values(**fields))


async def delete_exam(session: AsyncSession, exam_id: uuid.UUID) -> None:
    """Delete the row and flush, so a `RESTRICT` foreign key fails here.

    The `flush()` is deliberate: without it the `DELETE` sits unsent until
    something else touches the session, and the constraint violation would
    surface at a wildly unrelated point in the request instead of inside
    `service_authoring.delete_exam`'s `try`.
    """
    await session.execute(delete(Exam).where(Exam.id == exam_id))
    await session.flush()


async def pilot_exam_codes(session: AsyncSession) -> list[str]:
    """Exams a partner attribution link may name.

    Consumer-side, so platform exams only: a partner link is a B2C funnel and
    can never name an institution's private exam.
    """
    stmt = select(Exam.code).where(Exam.partner_pilot.is_(True), Exam.org_id.is_(None)).order_by(Exam.code)
    return [code for code in (await session.execute(stmt)).scalars()]


async def exam_by_id(session: AsyncSession, exam_id: uuid.UUID) -> Exam | None:
    """One exam by id, with no visibility filter.

    By id and unscoped deliberately: an attempt sat last year has to render
    whoever owns the exam it named. The callers that must not cross an owner
    boundary check ownership themselves, in the service.
    """
    return (await session.execute(select(Exam).where(Exam.id == exam_id))).scalar_one_or_none()


async def exam_code_by_id(session: AsyncSession, exam_id: uuid.UUID) -> str | None:
    """Exam code only, without loading the rest of the row."""
    result = await session.execute(select(Exam.code).where(Exam.id == exam_id))
    return result.scalar_one_or_none()


async def exam_codes_by_id(session: AsyncSession, exam_ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    """Batch lookup for list endpoints that would otherwise N+1 the exams table."""
    if not exam_ids:
        return {}
    result = await session.execute(select(Exam.id, Exam.code).where(Exam.id.in_(exam_ids)))
    return {exam_id: str(code) for exam_id, code in result.all()}


async def exam_ids_matching_code(session: AsyncSession, term: str) -> list[uuid.UUID]:
    """Ids of every exam whose code contains `term`, case-insensitively. For
    another slice's own search filter, so it never queries `exams` itself."""
    stmt = select(Exam.id).where(contains_text(Exam.code, term))
    return list((await session.execute(stmt)).scalars())


async def create_programme(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    exam_id: uuid.UUID,
    source: str = "custom",
    status: str | None = None,
    import_ref: dict[str, Any] | None = None,
) -> Programme:
    """Record that this organisation now runs the named exam.

    `status` left `None` keeps the column's own default (`draft`); an import passes
    `active` because the administrator asked for the exam in order to use it.
    """
    programme = Programme(
        org_id=org_id,
        exam_id=exam_id,
        source=source,
        import_ref=import_ref,
        **({"status": status} if status is not None else {}),
    )
    session.add(programme)
    await session.flush()
    await session.refresh(programme)
    return programme


async def programme_for_exam(
    session: AsyncSession, org_id: uuid.UUID, exam_id: uuid.UUID
) -> Programme | None:
    """Whether this organisation already runs the given exam, for the uniqueness check."""
    stmt = select(Programme).where(Programme.org_id == org_id, Programme.exam_id == exam_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def programme_by_id(
    session: AsyncSession, org_id: uuid.UUID, programme_id: uuid.UUID
) -> Programme | None:
    """One of this organisation's own programmes, by id."""
    stmt = select(Programme).where(Programme.org_id == org_id, Programme.id == programme_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_programmes(
    session: AsyncSession, org_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None = None
) -> tuple[list[tuple[Programme, Exam]], str | None]:
    """This organisation's programmes, each paired with the exam it names."""
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
    exam_ids = {programme.exam_id for programme in programmes}
    exams = {
        exam.id: exam for exam in (await session.execute(select(Exam).where(Exam.id.in_(exam_ids)))).scalars()
    }
    return [(programme, exams[programme.exam_id]) for programme in programmes], next_cursor


async def set_programme_status(
    session: AsyncSession, org_id: uuid.UUID, programme_id: uuid.UUID, *, status: str
) -> None:
    """Move a programme to a new status, such as pausing or resuming it."""
    await session.execute(
        update(Programme)
        .where(Programme.org_id == org_id, Programme.id == programme_id)
        .values(status=status)
    )


async def programme_names(
    session: AsyncSession, org_id: uuid.UUID, programme_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, str]:
    """The exam name each of this organisation's programmes offers, in one query."""
    if not programme_ids:
        return {}
    stmt = (
        select(Programme.id, Exam.name)
        .join(Exam, Exam.id == Programme.exam_id)
        .where(Programme.org_id == org_id, Programme.id.in_(list(programme_ids)))
    )
    return {programme_id: name for programme_id, name in (await session.execute(stmt)).all()}


async def exams_by_ids(session: AsyncSession, exam_ids: Sequence[uuid.UUID]) -> list[Exam]:
    """Every exam row named by these ids, in one query."""
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


async def org_exam_ids(session: AsyncSession, org_id: uuid.UUID) -> list[uuid.UUID]:
    """Which exams this organisation offers. A programme *is* that statement."""
    stmt = select(Programme.exam_id).where(Programme.org_id == org_id).distinct()
    return list((await session.execute(stmt)).scalars())
