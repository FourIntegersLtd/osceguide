"""Resolving an exam, and handing other slices a reference to it.

Writing one lives in `service_authoring`; offering one as a programme lives in
`service_programmes`.

`org_id` scopes every read here: `None` means the consumer catalogue; an
institution's exams are visible only to itself.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import cache
from app.core.exam_settings import ExamSettings
from app.core.settings import get_settings
from app.features.catalog import domain, repository
from app.features.catalog.errors import ProgrammeNotActive, ProgrammeNotFound, UnknownExamError
from app.features.catalog.models import Exam
from app.features.catalog.schemas import ExamRead

# The cache version every exam or programme write bumps; see `bump_catalog`.
CATALOG_VERSION = "catalog"


def bump_catalog(session: AsyncSession) -> None:
    """Make the cached exam codes and per-organisation exam lists unreachable once this commits."""
    cache.bump_after_commit(session, CATALOG_VERSION)


async def count_live_exams_for_rubric_version(session: AsyncSession, rubric_version_id: uuid.UUID) -> int:
    """How many exams not yet retired are marked against this rubric version."""
    return await repository.count_live_exams_for_rubric_version(session, rubric_version_id)


async def live_exam_names_by_rubric_version(
    session: AsyncSession, org_id: uuid.UUID | None, rubric_version_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[str]]:
    """Names of this owner's own exams not yet retired, by the rubric version each is marked against."""
    return await repository.live_exam_names_by_rubric_version(session, org_id, rubric_version_ids)


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

    Never defaulted: b2c once fell back to `sca` for an unrecognised `app_type`,
    which marked CASC transcripts against a GP rubric prompt.

    A draft or retired exam is refused as firmly as one that does not exist.
    `org_id` is the caller's scope: an institution resolves its own exams plus
    the platform catalogue; `None` resolves the catalogue only.
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
    """Map a stored exam onto what a route returns."""
    return ExamRead(
        id=exam.id,
        revision=exam.revision,
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
        settings=exam_settings(exam),
    )


def exam_settings(exam: Exam) -> ExamSettings:
    """The exam's stored settings, with every missing field at its default."""
    return ExamSettings.model_validate(exam.settings or {})


async def exam_settings_for_code(
    session: AsyncSession, code: str | None, *, org_id: uuid.UUID | None = None
) -> ExamSettings:
    """The settings of the exam with this code, or the defaults when there is no such exam.

    For generation and presentation, where an unknown or missing exam should
    behave like a plain exam rather than refuse: nothing is marked from this.
    """
    if not code or not code.strip():
        return ExamSettings()
    exam = await repository.exam_by_code(session, org_id, code)
    return ExamSettings() if exam is None else exam_settings(exam)


async def exam_settings_by_id(session: AsyncSession, exam_id: uuid.UUID | None) -> ExamSettings:
    """The settings of one exam by id, or the defaults when it is gone or not given."""
    exam = None if exam_id is None else await repository.exam_by_id(session, exam_id)
    return ExamSettings() if exam is None else exam_settings(exam)


async def exam_read_by_code(
    session: AsyncSession, code: str | None, *, org_id: uuid.UUID | None = None
) -> ExamRead | None:
    """The exam with this code as a route returns it, whatever its status, or `None`."""
    if not code or not code.strip():
        return None
    exam = await repository.exam_by_code(session, org_id, code)
    return None if exam is None else exam_read(exam)


def _framework_id(exam: Exam) -> str:
    """The id a stored result records against: the rubric version's own id, so
    it traces back to the exact wording it was marked against."""
    return str(exam.rubric_version_id) if exam.rubric_version_id else ""


async def exam_for_attempt(session: AsyncSession, exam_id: uuid.UUID) -> Exam:
    """The exam row an attempt was created against, by id with no status check.

    An attempt against a since-retired exam must still render and mark;
    `resolve_exam` is the one that refuses anything unpublished. Returns the
    full row because rendering needs its code, rubric and timings together.
    """
    exam = await repository.exam_by_id(session, exam_id)
    if exam is None:
        raise UnknownExamError(f"No exam with id {exam_id}.")
    return exam


async def exam_codes_by_id(session: AsyncSession, exam_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, str]:
    """Codes for a set of exam ids, in one query rather than one per row."""
    exams = await repository.exams_by_ids(session, list(exam_ids))
    return {exam.id: exam.code for exam in exams}


@dataclass(frozen=True)
class ExamRef:
    """An exam as another slice sees it: plain fields, not the mapped row, so a
    caller cannot lazily load attributes that stay inside this slice."""

    id: uuid.UUID
    code: str
    name: str
    framework_id: str
    station_attempt_limit: int
    status: str = "published"
    owner_kind: str = "platform"
    org_id: uuid.UUID | None = None


async def exam_ref_by_id(session: AsyncSession, exam_id: uuid.UUID) -> ExamRef | None:
    """The plain-field reference another slice can hold, or `None` if the exam is gone."""
    exam = await repository.exam_by_id(session, exam_id)
    return None if exam is None else _exam_ref(exam)


def _exam_ref(exam: Exam) -> ExamRef:
    """Map a stored exam onto the reference other slices are allowed to see."""
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


async def exam_refs_by_ids(session: AsyncSession, exam_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, ExamRef]:
    """References for a set of exam ids, keyed by id, in one query rather than one per row."""
    return {exam.id: _exam_ref(exam) for exam in await repository.exams_by_ids(session, list(exam_ids))}


async def exam_offered_by_org(session: AsyncSession, org_id: uuid.UUID, exam_id: uuid.UUID) -> ExamRef:
    """The exam, if this organisation may hand out access to it; otherwise `UnknownExamError`.

    Two ways qualify, and the exam must be published either way: the institution wrote it
    itself, or it is a platform exam the institution has imported (a programme names it).
    Merely being visible is not enough — every institution can see the whole platform
    catalogue, and seeing an exam is not the same as having taken it on. Another
    organisation's exam and a missing one get the same refusal, so ids cannot be probed.
    """
    exam = await repository.exam_by_id(session, exam_id)
    if exam is None or exam.status != domain.ExamStatus.PUBLISHED:
        raise UnknownExamError(f"No exam with id {exam_id} is offered here.")
    if exam.org_id == org_id:
        return _exam_ref(exam)
    if exam.org_id is None and await repository.programme_for_exam(session, org_id, exam.id) is not None:
        return _exam_ref(exam)
    raise UnknownExamError(f"No exam with id {exam_id} is offered here.")


async def exam_code_by_id(session: AsyncSession, exam_id: uuid.UUID) -> str | None:
    """The code of one exam, for a row that stores only its id."""
    exam = await repository.exam_by_id(session, exam_id)
    return None if exam is None else exam.code


async def exam_ids_matching_code(session: AsyncSession, term: str) -> list[uuid.UUID]:
    """Ids of every exam whose code contains `term`. For another slice's own
    search filter, so it never queries `exams` itself."""
    return await repository.exam_ids_matching_code(session, term)


async def exam_codes(session: AsyncSession, org_id: uuid.UUID | None = None) -> list[str]:
    """Every published exam's code this caller may see. Small enough not to page.

    Cached for `library_cache_seconds` under the "catalog" version, which every exam or programme
    write bumps once it commits (`bump_catalog`).
    """

    async def load() -> list[str]:
        return [exam.code for exam in await _published(session, org_id)]

    return await cache.get_or_load(
        f"catalog:exam-codes:{org_id or 'platform'}:v{await cache.version(CATALOG_VERSION)}",
        get_settings().library_cache_seconds,
        load,
        dump=json.dumps,
        parse=json.loads,
    )


async def exam_refs(session: AsyncSession, org_id: uuid.UUID | None = None) -> list[ExamRef]:
    """Every published exam this caller may see. Small enough not to page."""
    return [_exam_ref(exam) for exam in await _published(session, org_id)]


async def _published(session: AsyncSession, org_id: uuid.UUID | None = None) -> list[Exam]:
    return await repository.list_exams(session, org_id, statuses=[domain.ExamStatus.PUBLISHED])


async def ensure_programme_active(session: AsyncSession, org_id: uuid.UUID, programme_id: uuid.UUID) -> Exam:
    """The exam a programme offers, if the programme is running and its exam still published (S-24)."""
    programme = await repository.programme_by_id(session, org_id, programme_id)
    if programme is None:
        raise ProgrammeNotFound()
    exam = await exam_row(session, programme.exam_id)
    try:
        domain.ensure_offerable(exam.status)
    except domain.NotOfferable as exc:
        raise ProgrammeNotActive() from exc
    if not domain.ProgrammeRef(exam_code=exam.code, status=programme.status).is_offerable:
        raise ProgrammeNotActive()
    return exam


async def programme_exams(
    session: AsyncSession, org_id: uuid.UUID, programme_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, tuple[str, str]]:
    """A programme is shown by its exam's name; the code filters a station library."""
    return await repository.programme_exams(session, org_id, programme_ids)


async def count_programmes_with_markable_exam(session: AsyncSession, org_id: uuid.UUID) -> int:
    """Programmes whose exam is published and names a rubric version."""
    return await repository.count_programmes_with_markable_exam(session, org_id)


async def org_exam_ids(session: AsyncSession, org_id: uuid.UUID) -> list[uuid.UUID]:
    """The exams this organisation offers, through its programmes. Cached like `exam_codes`."""

    async def load() -> list[uuid.UUID]:
        return await repository.org_exam_ids(session, org_id)

    return await cache.get_or_load(
        f"catalog:org-exams:{org_id}:v{await cache.version(CATALOG_VERSION)}",
        get_settings().library_cache_seconds,
        load,
        dump=lambda ids: json.dumps([str(exam_id) for exam_id in ids]),
        parse=lambda raw: [uuid.UUID(exam_id) for exam_id in json.loads(raw)],
    )


async def has_published_exam(session: AsyncSession, org_id: uuid.UUID) -> bool:
    """Whether the organisation has published an exam of its own, not the platform's."""
    return await repository.has_published_exam(session, org_id)


async def offers_platform_exam(
    session: AsyncSession, org_id: uuid.UUID, *, with_rubric: bool = False
) -> bool:
    """Whether an offerable programme of the organisation offers a published platform exam (adopted)."""
    return await repository.offers_platform_exam(session, org_id)
