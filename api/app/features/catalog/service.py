"""Using an exam: resolving one, and handing another slice a reference to it.

Writing one lives in `service_authoring`; offering one as a programme lives in
`service_programmes`. Nine slices import `resolve_exam` from here, which is why
the reading half kept the module name.

An exam has an owner. The platform's exams are the consumer catalogue, visible
to everyone. An institution's are its own, visible to it alone, which is why
every read here takes the caller's scope: `org_id=None` means the consumer
catalogue, and a school's private exam can never be named from outside it.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog import domain, repository
from app.features.catalog.errors import ProgrammeNotFound, UnknownExamError
from app.features.catalog.models import Exam
from app.features.catalog.schemas import ExamRead


async def pilot_exam_codes(session: AsyncSession) -> frozenset[str]:
    """Which exams a partner attribution link may name. Platform-side only."""
    return frozenset(await repository.pilot_exam_codes(session))


async def exam_row(session: AsyncSession, exam_id: uuid.UUID) -> Exam:
    """One exam by id, or the refusal. Shared with `service_authoring`."""
    exam = await repository.exam_by_id(session, exam_id)
    if exam is None:
        raise UnknownExamError(f"No exam with id {exam_id}.")
    return exam


async def resolve_exam(session: AsyncSession, code: str, *, org_id: uuid.UUID | None = None) -> Exam:
    """Look a published exam up by code, refusing anything else.

    Never defaulted. b2c fell back to `sca` for an unrecognised `app_type`,
    which is how CASC transcripts came to be marked with a GP rubric prompt.

    A draft or retired exam is refused here as firmly as one that does not
    exist: this is what programmes, entitlements, stations and plans are built
    on, and none of them should be able to name an exam nobody can sit.

    `org_id` is the caller's scope. An institution resolves its own exams and
    the platform catalogue; a consumer caller (`None`) resolves the catalogue
    only, so one school's private exam code can never be named from outside it.
    """
    try:
        normalised = domain.normalise_code(code)
    except domain.InvalidExamCode as exc:
        raise UnknownExamError(str(exc)) from exc
    exam = await repository.exam_by_code(session, org_id, normalised)
    if exam is None:
        raise UnknownExamError(f"No exam with the code {normalised!r}.")
    try:
        domain.ensure_offerable(exam.status)
    except domain.NotOfferable as exc:
        raise UnknownExamError(str(exc)) from exc
    return exam


def exam_read(exam: Exam) -> ExamRead:
    return ExamRead(
        id=exam.id,
        owner_kind=exam.owner_kind,
        org_id=exam.org_id,
        code=exam.code,
        name=exam.name,
        status=exam.status,
        rubric_version_id=exam.rubric_version_id,
        framework_id=_framework_id(exam),
        default_reading_seconds=exam.default_reading_seconds,
        default_simulation_seconds=exam.default_simulation_seconds,
        station_attempt_limit=exam.station_attempt_limit,
        partner_pilot=exam.partner_pilot,
    )


def _framework_id(exam: Exam) -> str:
    """The id everything downstream records a result under.

    It is the rubric version's own id, so a stored result traces back to the
    exact wording it was marked against. It used to be a string column on the
    exam (`sca-rcgp-v1`), which named a framework the engine shipped and could
    not be changed without a release.
    """
    return str(exam.rubric_version_id) if exam.rubric_version_id else ""


async def exam_for_attempt(session: AsyncSession, exam_id: uuid.UUID) -> Exam:
    """The exam row an attempt was created against.

    By id and with no status check, deliberately: an attempt sat last year
    against an exam that has since been retired must still render and still
    mark. `resolve_exam` is the one that refuses anything unpublished, because
    that is the path new things are built on.

    Returns the row rather than a field, because rendering needs its code, its
    rubric and its timings together and there is no reason to read it three
    times.
    """
    exam = await repository.exam_by_id(session, exam_id)
    if exam is None:
        raise UnknownExamError(f"No exam with id {exam_id}.")
    return exam


async def exam_codes_by_id(session: AsyncSession, exam_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, str]:
    """Codes for a set of exam ids, in one query.

    Every list of stations, attempts or entitlements shows an exam code beside
    each row, and each of them resolved it one row at a time.
    """
    rows = await repository.exams_by_ids(session, list(exam_ids))
    return {row.id: row.code for row in rows}


@dataclass(frozen=True)
class ExamRef:
    """An exam, as another slice may see one.

    Not the mapped row: those stay inside this slice, and a caller that holds
    one can lazily load whatever it is attached to. Carries the fields other
    slices actually use — the code they display and the limits they enforce.
    """

    id: uuid.UUID
    code: str
    name: str
    framework_id: str
    station_attempt_limit: int
    status: str = "published"
    owner_kind: str = "platform"
    org_id: uuid.UUID | None = None


async def exam_ref_by_id(session: AsyncSession, exam_id: uuid.UUID) -> ExamRef | None:
    exam = await repository.exam_by_id(session, exam_id)
    return None if exam is None else _exam_ref(exam)


def _exam_ref(exam: Exam) -> ExamRef:
    return ExamRef(
        id=exam.id,
        code=exam.code,
        name=exam.name,
        framework_id=_framework_id(exam),
        station_attempt_limit=exam.station_attempt_limit,
        status=exam.status,
        owner_kind=exam.owner_kind,
        org_id=exam.org_id,
    )


async def exam_code_by_id(session: AsyncSession, exam_id: uuid.UUID) -> str | None:
    """The code of one exam, for a row that stores an exam id.

    Nine slices needed this and each reached into this slice's repository for
    it, which put nine callers behind a table only this slice owns. None of
    them wanted an `Exam`; they all wanted the four letters on the screen.
    """
    exam = await repository.exam_by_id(session, exam_id)
    return None if exam is None else exam.code


async def exam_codes(session: AsyncSession, org_id: uuid.UUID | None = None) -> list[str]:
    """Every published exam's code this caller may see. Small enough not to page."""
    return [exam.code for exam in await _published(session, org_id)]


async def exam_refs(session: AsyncSession, org_id: uuid.UUID | None = None) -> list[ExamRef]:
    """Every published exam this caller may see. Small enough not to page."""
    return [_exam_ref(exam) for exam in await _published(session, org_id)]


async def _published(session: AsyncSession, org_id: uuid.UUID | None = None) -> list[Exam]:
    return await repository.list_exams(session, org_id, statuses=[domain.ExamStatus.PUBLISHED])


async def programme_exam_id(session: AsyncSession, org_id: uuid.UUID, programme_id: uuid.UUID) -> uuid.UUID:
    """The exam this programme offers, or the refusal."""
    programme = await repository.programme_by_id(session, org_id, programme_id)
    if programme is None:
        raise ProgrammeNotFound()
    return programme.exam_id


async def count_programmes_with_markable_exam(session: AsyncSession, org_id: uuid.UUID) -> int:
    """Programmes whose exam is published and names a rubric version."""
    return await repository.count_programmes_with_markable_exam(session, org_id)
