"""Routes for a learner to see, and forget, what the tutor remembers about them."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import InvalidInput, Unauthenticated, error_responses
from app.core.pagination import CursorParams, Page
from app.core.ports import ClockDep
from app.core.rate_limit import USER_WRITE, TooManyRequests, per_user
from app.core.tenancy import PlatformAdmin
from app.features.tutor_memory import errors, schemas, service, service_material

router = APIRouter(tags=["tutor-memory"])

Session = Annotated[AsyncSession, Depends(get_session)]


# This person's past debrief summaries, newest first, paged.
@router.get(
    "/me/debriefs",
    response_model=Page[schemas.DebriefSummaryRead],
    responses=error_responses(Unauthenticated, InvalidInput),
)
async def list_debriefs(
    principal: CurrentPrincipal,
    session: Session,
    params: Annotated[CursorParams, Depends()],
) -> Page[schemas.DebriefSummaryRead]:
    return await service.list_debriefs(session, principal.user_id, params)


@router.post(
    "/me/activity",
    response_model=schemas.ActivityAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(TooManyRequests, Unauthenticated),
    dependencies=[Depends(per_user(USER_WRITE))],
)
async def record_activity(
    body: schemas.ActivityBatch, principal: CurrentPrincipal, session: Session, clock: ClockDep
) -> schemas.ActivityAccepted:
    """What this person has been reading and practising. Accepted as a batch; a repeat is a
    success that records nothing."""
    return await service.record_activity(
        session, user_id=principal.user_id, events=body.events, now=clock.now()
    )


@router.get(
    "/me/tutor-memory",
    response_model=schemas.TutorMemoryRead,
    responses=error_responses(Unauthenticated),
)
async def read_tutor_memory(principal: CurrentPrincipal, session: Session) -> schemas.TutorMemoryRead:
    """Everything the tutor knows about you.

    A memory nobody can inspect is one nobody can correct, and the tutor speaks
    from this every time it opens its mouth.
    """
    return await service.read_memory(session, principal.user_id)


@router.delete(
    "/me/tutor-memory/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(Unauthenticated, errors.NoteNotFound),
)
async def forget_note(note_id: uuid.UUID, principal: CurrentPrincipal, session: Session) -> None:
    """Forget one thing. Somebody else's note is a 404, not a 403."""
    await service.forget_note(session, user_id=principal.user_id, note_id=note_id)


@router.delete(
    "/me/tutor-memory",
    response_model=schemas.ForgottenCounts,
    responses=error_responses(Unauthenticated),
)
async def forget_tutor_memory(
    principal: CurrentPrincipal,
    session: Session,
    include_debriefs: Annotated[bool, Query()] = False,
) -> schemas.ForgottenCounts:
    """Forget the lot, and say how much was forgotten.

    Debrief summaries are opt-in: they are also this doctor's own record of
    what a debrief concluded, shown on their results.
    """
    return await service.forget_everything(
        session, user_id=principal.user_id, include_debriefs=include_debriefs
    )


@router.post(
    "/admin/tutor-memory/reindex",
    response_model=schemas.ReindexReport,
    responses=error_responses(Unauthenticated),
)
async def reindex_material(admin: PlatformAdmin, session: Session) -> schemas.ReindexReport:
    """Rebuild the material index now, rather than waiting for tonight's run. Synchronous:
    the response confirms the material is searchable."""
    run = await service_material.reindex(session)
    return schemas.ReindexReport(sources=run.sources, passages=run.passages, retired=run.retired)
