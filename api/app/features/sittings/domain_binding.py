"""Which rubric version a sitting is marked against.

A sitting names a programme; the programme's exam names a published rubric
version. Pure resolution logic lives next to the use case that enforces it.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog import repository as catalog_repo
from app.features.catalog import service as catalog
from app.features.catalog.errors import ProgrammeNotFound
from app.features.rubrics import service_marking
from app.features.sittings import errors


async def rubric_version_for_programme(
    session: AsyncSession, org_id: uuid.UUID, programme_id: uuid.UUID
) -> uuid.UUID:
    """The published rubric version this programme's exam is marked with."""
    programme = await catalog_repo.programme_by_id(session, org_id, programme_id)
    if programme is None:
        raise ProgrammeNotFound()
    exam = await catalog.exam_row(session, programme.exam_id)
    if exam.rubric_version_id is None:
        raise errors.ExamRubricNotReady(
            "That programme's exam has no published rubric to mark against yet."
        )
    await service_marking.published_version(session, org_id, exam.rubric_version_id)
    return exam.rubric_version_id
