"""Importing a station from an uploaded document.

Two steps, each a background job, with a person between them. The first drafts
a template from the document and stops, so the author reviews and publishes the
shape before anything is built on it. The second copies the document's words
into that published template and leaves a draft station. An upload that names
an already published template skips the first step.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import savepoint
from app.core.document_text import UnreadableDocument, extract_text
from app.core.errors import AppError
from app.core.events import publish_after_commit, user_topic
from app.core.jobs import allow_long_idle
from app.core.logging import get_logger
from app.core.settings import Settings
from app.features.catalog.errors import UnknownExamError as CatalogUnknownExam
from app.features.catalog.service import resolve_exam
from app.features.generation.errors import GenerationUnavailable
from app.features.stations import domain_imports, errors, station_import_drafting
from app.features.stations import repository_imports as repository
from app.features.stations import service as stations
from app.features.stations import service_templates as templates
from app.features.stations.jobs import enqueue_station_draft, enqueue_template_draft
from app.features.stations.models import StationImport
from app.features.stations.schemas import StationImportList, StationImportRead
from app.features.stations.station_content import station_block_ids

log = get_logger(__name__)

# One event for every change of an import's status. The payload is the import's
# id; the screen reads the row again.
STATION_IMPORT_UPDATED = "station_import.updated"

_MODEL_UNAVAILABLE = "The drafting service is not available right now. Try again in a few minutes."
_UNEXPECTED = "Something went wrong reading this file. Try again, or upload it again."


async def start_import(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    *,
    user_id: uuid.UUID,
    filename: str,
    content: bytes,
    exam_code: str,
    template_version_id: uuid.UUID | None,
) -> StationImportRead:
    """Take a PDF or Word document, read its text, and queue the first draft.

    With no template named the first job drafts one. With a published template
    named, the import goes straight to drafting the station.
    """
    try:
        domain_imports.validate_upload(filename=filename, size=len(content))
        text = domain_imports.ensure_usable_text(extract_text(filename, content))
    except (domain_imports.InvalidImport, UnreadableDocument) as exc:
        raise errors.InvalidImportFileError(str(exc)) from exc

    try:
        exam = await resolve_exam(session, exam_code, org_id=org_id)
    except CatalogUnknownExam as exc:
        raise errors.UnknownExamError(str(exc)) from exc

    stored_filename = filename[: domain_imports.MAX_FILENAME_CHARS]
    if template_version_id is None:
        station_import = await repository.create_import(
            session,
            org_id,
            created_by=user_id,
            exam_code=exam.code,
            original_filename=stored_filename,
            extracted_text=text,
            status=domain_imports.ImportStatus.DRAFTING_TEMPLATE.value,
        )
        await enqueue_template_draft(session, import_id=station_import.id)
        return _read(station_import)

    template_version = await templates.bindable_version(session, org_id, template_version_id)
    station_import = await repository.create_import(
        session,
        org_id,
        created_by=user_id,
        exam_code=exam.code,
        original_filename=stored_filename,
        extracted_text=text,
        status=domain_imports.ImportStatus.DRAFTING_STATION.value,
        template_id=template_version.template_id,
        template_version_id=template_version.id,
    )
    await enqueue_station_draft(session, import_id=station_import.id)
    return _read(station_import)


async def request_station(
    session: AsyncSession, org_id: uuid.UUID | None, import_id: uuid.UUID
) -> StationImportRead:
    """Queue the station draft for an import whose template has been published.

    Refused while the template is still a draft, so the author is told to
    publish it here rather than by a job failing a minute later.
    """
    station_import = await _require_import(session, org_id, import_id)
    if not domain_imports.may_draft_station(
        station_import.status, has_template=station_import.template_version_id is not None
    ):
        raise errors.ImportNotReadyError()
    assert station_import.template_version_id is not None  # noqa: S101 - narrowed by may_draft_station
    await templates.bindable_version(session, org_id, station_import.template_version_id)
    station_import = await repository.save_progress(
        session,
        station_import,
        status=domain_imports.ImportStatus.DRAFTING_STATION.value,
        error=None,
    )
    await enqueue_station_draft(session, import_id=station_import.id)
    return _read(station_import)


async def read_import(
    session: AsyncSession, org_id: uuid.UUID | None, import_id: uuid.UUID
) -> StationImportRead:
    """One import this owner uploaded. Another owner's is `not found`."""
    return _read(await _require_import(session, org_id, import_id))


async def list_imports(session: AsyncSession, org_id: uuid.UUID | None) -> StationImportList:
    """This owner's most recent imports, newest first."""
    station_imports = await repository.recent_imports(session, org_id, limit=domain_imports.RECENT_LIMIT)
    return StationImportList(imports=[_read(station_import) for station_import in station_imports])


async def run_template_job(session: AsyncSession, import_id: uuid.UUID, *, settings: Settings) -> None:
    """Draft a template from one import's text and stop for a person to review it.

    Idempotent: an import that is no longer `drafting_template` has already
    been through this step, so a redelivery does nothing.
    """
    station_import = await repository.get_for_job(session, import_id)
    if station_import is None or station_import.status != domain_imports.ImportStatus.DRAFTING_TEMPLATE.value:
        return
    org_id, exam_code, source_text = (
        station_import.org_id,
        station_import.exam_code,
        station_import.extracted_text,
    )

    async def draft() -> dict[str, object]:
        """Ask the model for the template and store it as a draft."""
        await allow_long_idle(session)
        drafted = await station_import_drafting.draft_template_structure(source_text, settings=settings)
        template = await templates.create_template(
            session, org_id, title=drafted.title, exam_code=exam_code, structure=drafted.structure
        )
        return {
            "status": domain_imports.ImportStatus.TEMPLATE_READY.value,
            "template_id": template.id,
            "template_version_id": template.versions[0].id,
        }

    await _run_step(session, station_import, draft)


async def run_station_job(session: AsyncSession, import_id: uuid.UUID, *, settings: Settings) -> None:
    """Copy one import's text into its published template and leave a draft station.

    Idempotent: an import that is no longer `drafting_station` has already been
    through this step, so a redelivery does not write a second station.
    """
    station_import = await repository.get_for_job(session, import_id)
    if (
        station_import is None
        or station_import.status != domain_imports.ImportStatus.DRAFTING_STATION.value
        or station_import.template_version_id is None
    ):
        return
    org_id, exam_code, source_text, filename, template_version_id = (
        station_import.org_id,
        station_import.exam_code,
        station_import.extracted_text,
        station_import.original_filename,
        station_import.template_version_id,
    )

    async def draft() -> dict[str, object]:
        """Ask the model to copy the document into the template, and store the draft station."""
        await allow_long_idle(session)
        template_version = await templates.bindable_version(session, org_id, template_version_id)
        structure = dict(template_version.structure)
        transcribed = await station_import_drafting.transcribe_station(
            source_text, structure, settings=settings
        )
        station = await stations.create_station(
            session,
            org_id,
            title=domain_imports.station_title(transcribed.title, filename),
            exam_code=exam_code,
            content=transcribed.content,
            template_version_id=template_version_id,
        )
        return {
            "status": domain_imports.ImportStatus.COMPLETED.value,
            "station_id": station.id,
            "review_notes": {
                "empty": domain_imports.empty_block_ids(station_block_ids(structure), transcribed.content),
                "reworded": domain_imports.reworded_block_ids(transcribed.content, source_text),
            },
        }

    await _run_step(session, station_import, draft)


async def _run_step(
    session: AsyncSession,
    station_import: StationImport,
    draft: Callable[[], Awaitable[dict[str, object]]],
) -> None:
    """Run one drafting step, record how it ended on the import, and tell the uploader.

    The step's writes sit in a savepoint, so a failure, even one after a flush,
    leaves no half-made template or station behind and the session still able
    to record it. The import is then marked `failed` with a reason a person can
    read, instead of staying in a drafting status forever.
    """
    import_id, created_by = station_import.id, station_import.created_by
    try:
        async with savepoint(session):
            changes = await draft()
    except GenerationUnavailable:
        changes = _failure(_MODEL_UNAVAILABLE)
    except (station_import_drafting.DraftingFailed, AppError) as exc:
        changes = _failure(str(exc))
    except Exception:  # noqa: BLE001 - any other failure must still settle the row
        log.exception("station import step failed", import_id=str(import_id))
        changes = _failure(_UNEXPECTED)
    await repository.save_progress(session, station_import, **changes)
    if created_by is not None:
        publish_after_commit(
            session, user_topic(created_by), STATION_IMPORT_UPDATED, {"import_id": str(import_id)}
        )


def _failure(reason: str) -> dict[str, object]:
    """The column changes that mark an import failed, with why."""
    return {"status": domain_imports.ImportStatus.FAILED.value, "error": reason}


async def _require_import(
    session: AsyncSession, org_id: uuid.UUID | None, import_id: uuid.UUID
) -> StationImport:
    """This owner's import by id, or refuse if there is no such import."""
    station_import = await repository.import_by_id(session, org_id, import_id)
    if station_import is None:
        raise errors.StationImportNotFound()
    return station_import


def _read(station_import: StationImport) -> StationImportRead:
    """Turn one stored import row into the shape the API returns."""
    review_notes = station_import.review_notes or {}
    return StationImportRead(
        id=station_import.id,
        status=domain_imports.ImportStatus(station_import.status),
        original_filename=station_import.original_filename,
        exam_code=station_import.exam_code,
        template_id=station_import.template_id,
        template_version_id=station_import.template_version_id,
        station_id=station_import.station_id,
        empty_block_ids=list(review_notes.get("empty") or []),
        reworded_block_ids=list(review_notes.get("reworded") or []),
        error=station_import.error,
        created_at=station_import.created_at,
    )
