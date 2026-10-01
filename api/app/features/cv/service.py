"""Uploading a CV, and reading it into sections.

Two moments, deliberately apart. The upload pulls the text out of the PDF and
writes a `processing` row — fast, and it is what the person waits on. The model
call that structures the text runs as a background job, so a slow model is a
slow job and not a slow request, and the row is there to be read back whether
or not the person keeps the tab open.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.document_text import UnreadableDocument, extract_pdf_text
from app.core.events import publish_after_commit, user_topic
from app.core.settings import Settings
from app.features.cv import domain, errors, llm, repository, schemas
from app.features.cv.jobs import enqueue_extraction
from app.features.cv.models import Cv

# Published to the owner's `/me/events` topic once the background reading job
# has an outcome, success or failure, so `CvPanel` learns without polling.
CV_READ = "cv.read"

UPLOAD_MESSAGE = "CV uploaded. We're reading it now and it will appear here shortly."


async def upload(
    session: AsyncSession, *, user_id: uuid.UUID, filename: str, content: bytes
) -> schemas.CvUploadResult:
    """Take a PDF, read its text, and queue the structuring."""
    try:
        domain.validate_upload(filename=filename, size=len(content))
    except domain.InvalidCv as exc:
        raise errors.InvalidCvFile(str(exc)) from exc

    try:
        raw = extract_pdf_text(content)
    except UnreadableDocument as exc:
        raise errors.InvalidCvFile(str(exc)) from exc

    try:
        text = domain.ensure_enough_text(raw)
    except domain.InvalidCv as exc:
        raise errors.InvalidCvFile(str(exc)) from exc

    cv = await repository.create(session, user_id=user_id, original_filename=filename, extracted_text=text)
    await enqueue_extraction(session, cv_id=cv.id)
    return schemas.CvUploadResult(id=cv.id, status=cv.status, message=UPLOAD_MESSAGE)


async def run_extraction_job(
    session: AsyncSession, cv_id: uuid.UUID, *, settings: Settings, now: datetime
) -> None:
    """Read one CV's text into sections, and record the outcome on its row.

    Idempotent: a row that is no longer `processing` has already been read, so
    a redelivery does nothing rather than overwriting a finished result.
    """
    cv = await repository.get(session, cv_id)
    if cv is None or cv.status != domain.Status.PROCESSING.value:
        return
    parsed, error = await llm.extract_structured(cv.extracted_text or "", settings=settings)
    if parsed is None:
        await repository.mark_failed(session, cv_id, error=error or "extraction failed", at=now)
        publish_after_commit(session, user_topic(cv.user_id), CV_READ, {"cv_id": str(cv_id)})
        return
    await repository.mark_completed(session, cv_id, structured=parsed.model_dump(), at=now)
    publish_after_commit(session, user_topic(cv.user_id), CV_READ, {"cv_id": str(cv_id)})


async def list_for_user(session: AsyncSession, user_id: uuid.UUID) -> schemas.CvList:
    """This person's own CVs, most recently uploaded first."""
    cvs_stored = await repository.list_for_user(session, user_id, limit=domain.RECENT_LIMIT)
    cvs = [_read(cv) for cv in cvs_stored]
    return schemas.CvList(cvs=cvs, total=len(cvs))


async def read(session: AsyncSession, cv_id: uuid.UUID, *, user_id: uuid.UUID) -> schemas.CvRead:
    """One CV, if it is yours. Somebody else's is `not found`, not `forbidden`."""
    cv = await repository.get(session, cv_id)
    if cv is None or cv.user_id != user_id:
        raise errors.CvNotFound()
    return _read(cv)


async def delete(session: AsyncSession, cv_id: uuid.UUID, *, user_id: uuid.UUID) -> None:
    """Throw your own CV away, whatever state it is in.

    Somebody else's is `not found`, not `forbidden` — the answer `read` gives, so an id still cannot
    be probed to learn whose it is. A hard delete: nothing else references `cvs`, and the row holds
    somebody's career history, so there is no reason to keep it once they asked for it to go.
    `processing` is not refused either — `run_extraction_job` tolerates the row being gone.
    """
    if not await repository.delete_cv(session, cv_id, user_id):
        raise errors.CvNotFound()


def _read(cv: Cv) -> schemas.CvRead:
    """Turn one stored CV row into the shape the API returns."""
    structured = schemas.StructuredCv.model_validate(cv.structured) if cv.structured else None
    return schemas.CvRead(
        id=cv.id,
        status=cv.status,
        original_filename=cv.original_filename,
        uploaded_at=cv.created_at,
        completed_at=cv.completed_at,
        structured=structured,
        error=cv.error,
    )
