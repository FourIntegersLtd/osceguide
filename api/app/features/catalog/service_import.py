"""An institution taking on one of the platform's published exams.

Replaces b2b's `seed-catalog` and `import-osce-guide`, which copied a bundle of stations
and a feedback template into the institution. Here nothing is copied: the platform exam
is adopted by reference, the way library stations are. Importing it records a programme
(`org_programmes`, source `imported_osce_guide`) naming the platform exam, and that
programme is what makes the exam the institution's to run sittings on and to grant
practice access to. The exam's stations and rubric stay the platform's and stay current.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.features.catalog import domain, repository
from app.features.catalog.errors import ExamAlreadyImported, UnknownExamError
from app.features.catalog.schemas import ExamRead, PlatformCatalogueExamRead
from app.features.catalog.service import exam_read
from app.features.stations import service_library_reads as station_library
from app.features.tenancy import service as tenancy

# The programme `source` an import writes, kept from b2b so a migrated row and a new one
# read the same.
IMPORTED_PROGRAMME_SOURCE = "imported_osce_guide"


async def platform_catalogue(session: AsyncSession, org_id: uuid.UUID) -> list[PlatformCatalogueExamRead]:
    """Every published platform exam, each marked with whether this institution already runs it.

    Platform drafts and retired exams are left out, and so is every institution's own exam:
    only what the platform currently offers can be imported.
    """
    platform_exams = await repository.list_exams(session, None, statuses=[domain.ExamStatus.PUBLISHED])
    imported_exam_ids = set(await repository.org_exam_ids(session, org_id))
    station_counts = await station_library.library_station_counts(
        session, [platform_exam.id for platform_exam in platform_exams]
    )
    return [
        PlatformCatalogueExamRead(
            exam_id=platform_exam.id,
            code=platform_exam.code,
            title=platform_exam.name,
            station_count=station_counts.get(platform_exam.id, 0),
            already_imported=platform_exam.id in imported_exam_ids,
        )
        for platform_exam in platform_exams
    ]


async def published_station_counts_by_code(session: AsyncSession, codes: Sequence[str]) -> dict[str, int]:
    """Published library stations per platform exam code, for the public pricing page.

    A code with no published exam or no stations reads zero, so every asked code is present.
    """
    exams = [
        exam
        for exam in await repository.list_exams(session, None, statuses=[domain.ExamStatus.PUBLISHED])
        if exam.code in codes
    ]
    counts = await station_library.library_station_counts(session, [exam.id for exam in exams])
    by_code = {exam.code: counts.get(exam.id, 0) for exam in exams}
    return {code: by_code.get(code, 0) for code in codes}


async def import_platform_exam(
    session: AsyncSession, org_id: uuid.UUID, *, platform_exam_id: uuid.UUID, actor: Principal
) -> ExamRead:
    """Bring a published platform exam into this institution, by reference.

    Refused `unknown_exam` (404) unless the id names a published platform exam: an
    institution's own exam, a draft or a retired one are all refused alike. Refused
    `exam_already_imported` (409) if the institution already runs it. The new programme
    is `active` straight away, since the administrator imported the exam in order to use it.
    """
    platform_exam = await repository.exam_by_id(session, platform_exam_id)
    if (
        platform_exam is None
        or platform_exam.org_id is not None
        or platform_exam.status != domain.ExamStatus.PUBLISHED
    ):
        raise UnknownExamError(f"No published platform exam with id {platform_exam_id}.")
    if await repository.programme_for_exam(session, org_id, platform_exam.id) is not None:
        raise ExamAlreadyImported()
    await repository.create_programme(
        session,
        org_id,
        exam_id=platform_exam.id,
        source=IMPORTED_PROGRAMME_SOURCE,
        status="active",
        import_ref={"platform_exam_id": str(platform_exam.id), "platform_exam_code": platform_exam.code},
    )
    await tenancy.record_audit(
        session,
        org_id=org_id,
        actor_user_id=actor.user_id,
        actor_email=actor.email,
        action="exam.imported",
        target_type="exam",
        target_id=str(platform_exam.id),
        summary=f"Imported {platform_exam.name} ({platform_exam.code}) from the platform catalogue",
    )
    return exam_read(platform_exam)
