"""HTTP routes for uploading, listing, reading and deleting a person's own CVs."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Unauthenticated, error_responses
from app.core.rate_limit import CV_UPLOAD, TooManyRequests, caller_key, check
from app.features.cv import errors, schemas, service

router = APIRouter(tags=["cv"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.post(
    "/cv",
    response_model=schemas.CvUploadResult,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Unauthenticated, errors.InvalidCvFile, TooManyRequests),
)
async def upload_cv(
    request: Request,
    principal: CurrentPrincipal,
    session: Session,
    file: Annotated[UploadFile, File(description="The CV, as a PDF")],
) -> schemas.CvUploadResult:
    """Upload a CV and queue reading it into sections.

    The first multipart route on this API. The text is pulled from the PDF here
    — it is cheap and it is what the size and type checks are for — and the
    model call that structures it is a background job, so the answer comes back
    before the reading is done. Rate limited: an upload pays for a parse and,
    behind it, a model call.
    """
    await check(CV_UPLOAD, caller_key(request))
    content = await file.read()
    return await service.upload(
        session, user_id=principal.user_id, filename=file.filename or "", content=content
    )


@router.get(
    "/cv",
    response_model=schemas.CvList,
    responses=error_responses(Unauthenticated),
)
async def list_cv(principal: CurrentPrincipal, session: Session) -> schemas.CvList:
    """Your own CVs, most recent first, with whatever has been read so far."""
    return await service.list_for_user(session, principal.user_id)


@router.get(
    "/cv/{cv_id}",
    response_model=schemas.CvRead,
    responses=error_responses(Unauthenticated, errors.CvNotFound),
)
async def read_cv(cv_id: uuid.UUID, principal: CurrentPrincipal, session: Session) -> schemas.CvRead:
    """One CV. Somebody else's is `not found`, so an id cannot be probed."""
    return await service.read(session, cv_id, user_id=principal.user_id)


@router.delete(
    "/cv/{cv_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(Unauthenticated, errors.CvNotFound),
)
async def delete_cv(cv_id: uuid.UUID, principal: CurrentPrincipal, session: Session) -> None:
    """Throw your own CV away, including one still being read.

    Somebody else's is `not found` rather than `forbidden`, the same answer a
    read gives, so a delete cannot be used to probe an id either.
    """
    await service.delete(session, cv_id, user_id=principal.user_id)
