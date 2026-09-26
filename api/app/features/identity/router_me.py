"""The profile routes: who am I, and what may I change about myself."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Unauthenticated, error_responses
from app.core.memberships import MembershipsFor
from app.core.ports import ClockDep
from app.features.identity import schemas, service, service_close_account
from app.features.identity.errors import ExamAlreadyChosen, InvalidCredentials, UnknownExamError

router = APIRouter(tags=["identity"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.patch(
    "/me",
    response_model=schemas.UserRead,
    responses=error_responses(Unauthenticated, ExamAlreadyChosen, UnknownExamError),
)
async def update_me(
    body: schemas.UpdateMe,
    principal: CurrentPrincipal,
    session: Annotated[AsyncSession, Depends(get_session)],
    memberships_for: MembershipsFor,
) -> schemas.UserRead:
    """Change a person's own profile: their name, their exam date, their
    reading-time arrangement, and their exam once if they have none.

    Only what was sent is written — `model_fields_set` rather than the whole
    body, so a screen that edits one field does not silently clear the others.
    """
    return await service.update_me(
        session,
        principal=principal,
        body=body,
        fields_sent=set(body.model_fields_set),
        memberships_for=memberships_for,
    )


@router.get("/me", response_model=schemas.UserRead, responses=error_responses(Unauthenticated))
async def read_me(
    principal: CurrentPrincipal,
    session: Annotated[AsyncSession, Depends(get_session)],
    memberships_for: MembershipsFor,
) -> schemas.UserRead:
    return await service.read_me(session, principal=principal, memberships_for=memberships_for)


@router.post(
    "/me/close",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(Unauthenticated, InvalidCredentials),
)
async def close_me(
    body: schemas.CloseAccount,
    principal: CurrentPrincipal,
    session: Annotated[AsyncSession, Depends(get_session)],
    clock: ClockDep,
) -> None:
    """Close this account. Sign-in stops; the consultations stay."""
    await service_close_account.close_account(
        session,
        user_id=principal.user_id,
        password=body.password,
        confirm=body.confirm,
        now=clock.now(),
    )
