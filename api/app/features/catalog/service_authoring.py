"""Writing an exam: who owns it, and when it is offered.

Reading an exam lives in `service.py`; every function here is owner-aware.

An exam has an owner: the platform writes the consumer catalogue, an
institution writes its own. Every function that changes an exam takes the
actor's `org_id` (`None` for a platform admin) and refuses to touch anyone
else's.
"""

from __future__ import annotations

import uuid
from typing import Any, Literal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exam_settings import ExamSettings
from app.features.catalog import domain, repository
from app.features.catalog.errors import (
    ExamCodeTaken,
    ExamInUse,
    ExamNotOwned,
    ExamNotPublishable,
    InvalidExamCodeError,
    InvalidExamSettings,
)
from app.features.catalog.models import Exam
from app.features.catalog.schemas import ExamRead
from app.features.catalog.service import exam_read, exam_row
from app.features.rubrics import service_marking as rubrics

ExamListStatus = Literal["published", "draft", "all"]


async def list_exams(
    session: AsyncSession,
    *,
    org_id: uuid.UUID | None = None,
    status: ExamListStatus = "published",
) -> list[ExamRead]:
    """What this caller may see, by `status`.

    `published` is the caller's own published exams plus the platform catalogue.
    `draft` is the caller's own drafts only. `all` is the caller's own exams in
    any status plus the platform's published ones. Another owner's drafts are
    never shown.
    """
    if status == "draft":
        exams = await repository.list_exams(
            session, org_id, statuses=[domain.ExamStatus.DRAFT], owned_only=True
        )
    else:
        exams = await repository.list_exams(
            session, org_id, statuses=[domain.ExamStatus.PUBLISHED], own_any_status=status == "all"
        )
    return [exam_read(exam) for exam in exams]


async def list_platform_exams(
    session: AsyncSession, *, status: str | None, limit: int, cursor: dict[str, Any] | None
) -> tuple[list[ExamRead], str | None]:
    """A page of the consumer catalogue as the console sees it: drafts and
    retired exams included, optionally narrowed to one status."""
    exams, next_cursor = await repository.list_platform_exams(
        session, status=status, limit=limit, cursor=cursor
    )
    return [exam_read(exam) for exam in exams], next_cursor


async def create_exam(
    session: AsyncSession,
    org_id: uuid.UUID | None = None,
    *,
    code: str,
    name: str,
    default_reading_seconds: int,
    default_simulation_seconds: int,
    station_attempt_limit: int = 3,
    rubric_version_id: uuid.UUID | None = None,
    partner_pilot: bool = False,
    settings: ExamSettings | None = None,
) -> ExamRead:
    """A new exam, as a draft. Nothing may be built on it until it is published.

    `org_id` is the author: `None` writes a platform exam, an org id writes
    that institution's own, with no list of platform exams to pick from.
    `settings` omitted stores `{}`, which reads back as every default.
    """
    try:
        normalised = domain.normalise_code(code)
    except domain.InvalidExamCode as exc:
        raise InvalidExamCodeError(str(exc)) from exc
    if await repository.owned_exam_by_code(session, org_id, normalised) is not None:
        raise ExamCodeTaken(f"An exam with the code {normalised!r} already exists.")
    if rubric_version_id is not None:
        await _usable_rubric(session, org_id, rubric_version_id)
    stored_settings = {} if settings is None else _storable_settings(settings)
    exam = await repository.create_exam(
        session,
        owner_kind=domain.owner_of(org_id),
        org_id=org_id,
        code=normalised,
        name=name,
        default_reading_seconds=default_reading_seconds,
        default_simulation_seconds=default_simulation_seconds,
        station_attempt_limit=station_attempt_limit,
        rubric_version_id=rubric_version_id,
        partner_pilot=partner_pilot and org_id is None,
        settings=stored_settings,
    )
    return exam_read(exam)


# Fields where an explicit null means "clear it"; for every other field null means "unchanged".
_CLEARABLE = frozenset({"rubric_version_id"})


async def update_exam(
    session: AsyncSession, exam_id: uuid.UUID, org_id: uuid.UUID | None = None, **fields: Any
) -> ExamRead:
    """Change an exam's name, timings or rubric. Its code is not editable.

    A code appears in plans, ref ids and URLs that already exist, so renaming
    one would silently strand them; a new exam is the honest way to do it.
    """
    exam = await _owned_exam(session, exam_id, org_id)
    changes = {field: value for field, value in fields.items() if value is not None or field in _CLEARABLE}
    if "rubric_version_id" in changes:
        if changes["rubric_version_id"] is None:
            # No existing code fits better: the refusal is "this exam cannot be offered without a
            # rubric", which is what `exam_not_publishable` already says to the screen.
            if exam.status != "draft":
                raise ExamNotPublishable("A published exam must keep its marking scheme version.")
        else:
            await _usable_rubric(session, org_id, changes["rubric_version_id"])
    if "settings" in changes:
        changes["settings"] = _storable_settings(ExamSettings.model_validate(changes["settings"]))
    if org_id is not None:
        # Partner attribution is a consumer funnel; an org exam is never in it.
        changes.pop("partner_pilot", None)
    await repository.update_exam(session, exam.id, **changes)
    return exam_read(await exam_row(session, exam_id))


async def publish_exam(
    session: AsyncSession, exam_id: uuid.UUID, org_id: uuid.UUID | None = None
) -> ExamRead:
    """Offer the exam. Only its own owner may, and only they decide when."""
    exam = await _owned_exam(session, exam_id, org_id)
    try:
        status = domain.ensure_publishable(exam.status, exam.rubric_version_id)
    except domain.NotPublishable as exc:
        raise ExamNotPublishable(str(exc)) from exc
    await repository.update_exam(session, exam.id, status=status)
    return exam_read(await exam_row(session, exam_id))


async def retire_exam(session: AsyncSession, exam_id: uuid.UUID, org_id: uuid.UUID | None = None) -> ExamRead:
    """Stop offering an exam without touching what was already attempted.

    An owner's own decision: retiring one institution's exam changes nothing
    for anyone else's programmes or past results.
    """
    exam = await _owned_exam(session, exam_id, org_id)
    try:
        status = domain.ensure_retirable(exam.status)
    except domain.NotRetirable as exc:
        raise ExamNotPublishable(str(exc)) from exc
    await repository.update_exam(session, exam.id, status=status)
    return exam_read(await exam_row(session, exam_id))


async def delete_exam(session: AsyncSession, exam_id: uuid.UUID, org_id: uuid.UUID) -> None:
    """Remove an org's own exam outright, if nothing was ever built on it.

    Org-scoped by construction — `org_id` is required, not `None` — so the
    platform catalogue keeps `retire` as its only lifecycle exit, the same as
    any exam that has actually been used.

    `catalog` cannot check "does anything reference this exam" itself, so the
    database's `RESTRICT` constraints are the check, caught here as
    `ExamInUse` rather than surfacing an unmapped `internal_error`.
    """
    exam = await _owned_exam(session, exam_id, org_id)
    try:
        await repository.delete_exam(session, exam.id)
    except IntegrityError as exc:
        raise ExamInUse() from exc


def _storable_settings(settings: ExamSettings) -> dict[str, Any]:
    """Settings as the JSON column stores them, refused if they name a prompt that does not exist.

    Checked here rather than at generation so a typo fails when the exam is
    saved, not later as a silent fallback to the default prompt.
    """
    # Imported here: generation reads `catalog.schemas`, so a module-level
    # import would make the two slices load each other.
    from app.features.generation import service as generation

    unknown = generation.unknown_prompt_keys(settings)
    if unknown:
        raise InvalidExamSettings(f"Unknown generation keys in settings: {', '.join(unknown)}.")
    return settings.model_dump(mode="json")


async def _owned_exam(session: AsyncSession, exam_id: uuid.UUID, org_id: uuid.UUID | None) -> Exam:
    """The exam this actor is allowed to change, or the same 404 as a stranger.

    Refused as not-found rather than forbidden: whether we are drafting an exam
    is not something an institution should be able to learn by guessing ids,
    and the same holds in reverse.
    """
    exam = await exam_row(session, exam_id)
    try:
        domain.ensure_owned_by(exam.org_id, org_id)
    except domain.NotOwned as exc:
        raise ExamNotOwned(str(exc)) from exc
    return exam


async def _usable_rubric(
    session: AsyncSession, org_id: uuid.UUID | None, rubric_version_id: uuid.UUID
) -> None:
    """What this owner's exam may be marked against.

    A platform exam names a platform rubric: it belongs to everyone, so it
    cannot be bound to one institution's. An institution's own exam may name
    its own published rubric or a platform one it can already read — otherwise
    authoring an exam would still mean waiting for us to write the rubric.
    """
    if org_id is None:
        await rubrics.published_platform_version(session, rubric_version_id)
    else:
        await rubrics.published_version(session, org_id, rubric_version_id)
