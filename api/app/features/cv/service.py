"""Uploading a CV, and reading it into sections.

Two moments, deliberately apart. The upload pulls the text out of the PDF and
writes a `processing` row — fast, and it is what the person waits on. The model
call that structures the text runs as a background job, so a slow model is a
slow job and not a slow request, and the row is there to be read back whether
or not the person keeps the tab open.
"""

from __future__ import annotations

import io
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import Settings
from app.features.cv import domain, errors, llm, repository, schemas
from app.features.cv.jobs import enqueue_extraction
from app.features.cv.models import Cv

UPLOAD_MESSAGE = "CV uploaded. We're reading it now and it will appear here shortly."


def _extract_text(content: bytes) -> str:
    """The text of a PDF, page by page.

    `pypdf` is imported here rather than at the top so the API starts and serves
    every route that is not a CV upload on a machine without it — the same
    tolerance the LiveKit SDK is given.
    """
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


async def upload(
    session: AsyncSession, *, user_id: uuid.UUID, filename: str, content: bytes
) -> schemas.CvUploadResult:
    """Take a PDF, read its text, and queue the structuring."""
    try:
        domain.validate_upload(filename=filename, size=len(content))
    except domain.InvalidCv as exc:
        raise errors.InvalidCvFile(str(exc)) from exc

    try:
        raw = _extract_text(content)
    except Exception as exc:  # noqa: BLE001 - a PDF pypdf cannot read is the person's problem, not a 500
        raise errors.InvalidCvFile("That file could not be read as a PDF.") from exc

    try:
        text = domain.ensure_enough_text(raw)
    except domain.InvalidCv as exc:
        raise errors.InvalidCvFile(str(exc)) from exc

    row = await repository.create(session, user_id=user_id, original_filename=filename, extracted_text=text)
    await enqueue_extraction(session, cv_id=row.id)
    return schemas.CvUploadResult(id=row.id, status=row.status, message=UPLOAD_MESSAGE)


async def run_extraction_job(
    session: AsyncSession, cv_id: uuid.UUID, *, settings: Settings, now: datetime
) -> None:
    """Read one CV's text into sections, and record the outcome on its row.

    Idempotent: a row that is no longer `processing` has already been read, so
    a redelivery does nothing rather than overwriting a finished result.
    """
    row = await repository.get(session, cv_id)
    if row is None or row.status != domain.Status.PROCESSING.value:
        return
    parsed, error = await llm.extract_structured(row.extracted_text or "", settings=settings)
    if parsed is None:
        await repository.mark_failed(session, cv_id, error=error or "extraction failed", at=now)
        return
    await repository.mark_completed(session, cv_id, structured=parsed.model_dump(), at=now)


async def list_for_user(session: AsyncSession, user_id: uuid.UUID) -> schemas.CvList:
    rows = await repository.list_for_user(session, user_id, limit=domain.RECENT_LIMIT)
    cvs = [_read(row) for row in rows]
    return schemas.CvList(cvs=cvs, total=len(cvs))


async def read(session: AsyncSession, cv_id: uuid.UUID, *, user_id: uuid.UUID) -> schemas.CvRead:
    """One CV, if it is yours. Somebody else's is `not found`, not `forbidden`."""
    row = await repository.get(session, cv_id)
    if row is None or row.user_id != user_id:
        raise errors.CvNotFound()
    return _read(row)


async def delete(session: AsyncSession, cv_id: uuid.UUID, *, user_id: uuid.UUID) -> None:
    """Throw your own CV away, whatever state it is in.

    Somebody else's is `not found`, not `forbidden` — the answer `read` gives, so an id still cannot
    be probed to learn whose it is. A hard delete: nothing else references `cvs`, and the row holds
    somebody's career history, so there is no reason to keep it once they asked for it to go.
    `processing` is not refused either — `run_extraction_job` tolerates the row being gone.
    """
    if not await repository.delete_cv(session, cv_id, user_id):
        raise errors.CvNotFound()


def _read(row: Cv) -> schemas.CvRead:
    structured = schemas.StructuredCv.model_validate(row.structured) if row.structured else None
    return schemas.CvRead(
        id=row.id,
        status=row.status,
        original_filename=row.original_filename,
        uploaded_at=row.created_at,
        completed_at=row.completed_at,
        structured=structured,
        error=row.error,
    )
