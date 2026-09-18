"""Writing an exam: who owns it, and when it is offered.

Split from `service.py` along the line the slice already divides on. That
module is about *using* an exam — resolving one, handing another slice a ref.
This one is about writing one, and every function here is owner-aware.

An exam has an owner. The platform writes the consumer catalogue; an
institution writes its own, on its own schedule, without either arm waiting on
the other. Every function that changes an exam takes the actor's `org_id` —
`None` for a platform admin — and refuses to touch somebody else's.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog import domain, repository
from app.features.catalog.errors import (
    ExamCodeTaken,
    ExamNotOwned,
    ExamNotPublishable,
    InvalidExamCodeError,
)
from app.features.catalog.models import Exam
from app.features.catalog.schemas import ExamRead
from app.features.catalog.service import exam_read, exam_row
from app.features.rubrics import service_marking as rubrics


async def list_exams(
    session: AsyncSession,
    *,
    org_id: uuid.UUID | None = None,
    include_unpublished: bool = False,
) -> list[ExamRead]:
    """What this caller may see: their own exams, plus the platform catalogue.

    Drafts are shown only to the owner that wrote them, so `include_unpublished`
    narrows the listing to this caller's own rows rather than widening it. A
    platform admin must not see what Ashford is drafting, and Ashford must not
    see what we are drafting — the same rule, from both sides.
    """
    if include_unpublished:
        return [exam_read(e) for e in await repository.list_exams(session, org_id, owned_only=True)]
    rows = await repository.list_exams(session, org_id, statuses=[domain.ExamStatus.PUBLISHED])
    return [exam_read(e) for e in rows]


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
) -> ExamRead:
    """A new exam, as a draft. Nothing may be built on it until it is published.

    `org_id` is the author: `None` writes a platform exam, an org id writes that
    institution's own. An institution does not ask us first and is not offered
    a list to pick from — that restriction is what made every school's
    programme a label on one of four rows we happened to have written.
    """
    try:
        normalised = domain.normalise_code(code)
    except domain.InvalidExamCode as exc:
        raise InvalidExamCodeError(str(exc)) from exc
    if await repository.owned_exam_by_code(session, org_id, normalised) is not None:
        raise ExamCodeTaken(f"An exam with the code {normalised!r} already exists.")
    if rubric_version_id is not None:
        await _usable_rubric(session, org_id, rubric_version_id)
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
    )
    return exam_read(exam)


async def update_exam(
    session: AsyncSession, exam_id: uuid.UUID, org_id: uuid.UUID | None = None, **fields: Any
) -> ExamRead:
    """Change an exam's name, timings or rubric. Its code is not editable.

    A code appears in plans, ref ids and URLs that already exist, so renaming
    one would silently strand them; a new exam is the honest way to do it.
    """
    exam = await _owned_exam(session, exam_id, org_id)
    changes = {k: v for k, v in fields.items() if v is not None}
    if "rubric_version_id" in changes:
        await _usable_rubric(session, org_id, changes["rubric_version_id"])
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

    An owner's own decision, and only theirs. Retiring the platform's PLAB
    leaves Ashford's programmes and their past results exactly where they were,
    and Ashford retiring its own exam changes nothing for anybody else.
    """
    exam = await _owned_exam(session, exam_id, org_id)
    try:
        status = domain.ensure_retirable(exam.status)
    except domain.NotRetirable as exc:
        raise ExamNotPublishable(str(exc)) from exc
    await repository.update_exam(session, exam.id, status=status)
    return exam_read(await exam_row(session, exam_id))


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
