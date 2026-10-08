"""The profile routes: who am I, and what may I change about myself."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Unauthenticated, error_responses
from app.core.events import get_event_bus, user_topic
from app.core.memberships import MembershipsFor
from app.core.openapi import fan_in_responses
from app.core.ports import ClockDep, EventBus
from app.core.rate_limit import USER_WRITE, TooManyRequests, caller_key, per_user
from app.core.settings import SettingsDep
from app.core.sse import MEDIA_TYPE, SSE_HEADERS, fan_in_stream
from app.core.streams import StreamPrincipal
from app.features.identity import schemas, service, service_close_account, service_export, service_mfa
from app.features.identity.errors import (
    AccountNotFound,
    ExamAlreadyChosen,
    InvalidAvatarFile,
    InvalidCredentials,
    InvalidMfaCode,
    MfaAlreadyEnrolled,
    MfaNotEnrolled,
    MfaRequiredByPolicy,
    UnknownExamError,
)

router = APIRouter(tags=["identity"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.patch(
    "/me",
    response_model=schemas.UserRead,
    responses=error_responses(Unauthenticated, AccountNotFound, ExamAlreadyChosen, UnknownExamError),
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


# Read the signed-in person's account and the workspaces they belong to.
@router.get(
    "/me", response_model=schemas.UserRead, responses=error_responses(Unauthenticated, AccountNotFound)
)
async def read_me(
    principal: CurrentPrincipal,
    session: Annotated[AsyncSession, Depends(get_session)],
    memberships_for: MembershipsFor,
) -> schemas.UserRead:
    return await service.read_me(session, principal=principal, memberships_for=memberships_for)


@router.post(
    "/me/avatar",
    response_model=schemas.UserRead,
    responses=error_responses(TooManyRequests, Unauthenticated, AccountNotFound, InvalidAvatarFile),
    dependencies=[Depends(per_user(USER_WRITE))],
)
async def upload_my_avatar(
    principal: CurrentPrincipal,
    session: Annotated[AsyncSession, Depends(get_session)],
    memberships_for: MembershipsFor,
    settings: SettingsDep,
    file: Annotated[UploadFile, File(description="A JPEG, PNG or WebP image")],
) -> schemas.UserRead:
    """Replace this person's profile photo. Refused if the file is not a
    small image; the previous photo is deleted from storage on success."""
    content = await file.read()
    return await service.upload_avatar(
        session,
        user_id=principal.user_id,
        content=content,
        content_type=file.content_type,
        settings=settings,
        memberships_for=memberships_for,
    )


@router.post(
    "/me/close",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(Unauthenticated, AccountNotFound, InvalidCredentials),
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


@router.get(
    "/me/export",
    response_model=schemas.MyDataExport,
    responses=error_responses(Unauthenticated, AccountNotFound),
)
async def export_me(
    principal: CurrentPrincipal,
    session: Annotated[AsyncSession, Depends(get_session)],
    response: Response,
) -> schemas.MyDataExport:
    """Download everything this account owns: profile, attempts with their
    transcripts and marks, and payments. Offered as an attachment, so the
    browser saves it rather than rendering it."""
    response.headers["Content-Disposition"] = "attachment; filename=my-data.json"
    return await service_export.export_my_data(session, user_id=principal.user_id)


@router.get(
    "/me/events",
    responses=fan_in_responses(Unauthenticated),
    response_class=StreamingResponse,
)
async def stream_my_events(
    principal: StreamPrincipal,
    bus: Annotated[EventBus, Depends(get_event_bus)],
) -> StreamingResponse:
    """One stream, every kind of thing that happens to this person.

    The one live-update connection a signed-in tab holds. Each frame names
    what happened (the events are listed on `MeEventEnvelope`) and
    carries just enough of a payload — an id — for a screen to tell whether it
    is the one being talked about; it still re-reads its own resource rather
    than trusting the frame's content as truth. Every screen that waits on
    something listens here and never asks on a timer: marking status, a
    partner's answer, a CV finishing, a live coverage panel, media production
    status.

    Unlike `/attempts/{id}/stream` or `/sittings/stream`, there is no single
    read model behind this route to snapshot, so it is built on
    `fan_in_stream` rather than `event_stream` — see `app.core.sse` for why.
    """
    return StreamingResponse(
        fan_in_stream(topics=[user_topic(principal.user_id)], bus=bus),
        media_type=MEDIA_TYPE,
        headers=SSE_HEADERS,
    )


# Whether this account has an authenticator, and whether policy requires one.
@router.get(
    "/me/mfa",
    response_model=schemas.MfaStatusRead,
    responses=error_responses(Unauthenticated),
)
async def read_my_mfa(principal: CurrentPrincipal, session: Session) -> schemas.MfaStatusRead:
    return await service_mfa.read_status(
        session, user_id=principal.user_id, is_platform_admin=principal.is_platform_admin
    )


# Start authenticator enrolment from an existing session.
@router.post(
    "/me/mfa/enrol",
    response_model=schemas.MfaEnrolmentStart,
    responses=error_responses(Unauthenticated, MfaAlreadyEnrolled),
)
async def start_my_mfa_enrolment(
    principal: CurrentPrincipal,
    session: Session,
    settings: SettingsDep,
    clock: ClockDep,
) -> schemas.MfaEnrolmentStart:
    return await service_mfa.start_enrolment_for_user(
        session, user_id=principal.user_id, settings=settings, now=clock.now()
    )


# Confirm that authenticator. Recovery codes are in this response only.
@router.post(
    "/me/mfa/confirm",
    response_model=schemas.MfaRecoveryCodesRead,
    responses=error_responses(
        Unauthenticated, InvalidMfaCode, MfaNotEnrolled, MfaAlreadyEnrolled, TooManyRequests
    ),
)
async def confirm_my_mfa(
    request: Request,
    body: schemas.MfaCodeRequest,
    principal: CurrentPrincipal,
    session: Session,
    settings: SettingsDep,
    clock: ClockDep,
) -> schemas.MfaRecoveryCodesRead:
    return await service_mfa.confirm_enrolment_for_user(
        session,
        user_id=principal.user_id,
        code=body.code,
        settings=settings,
        now=clock.now(),
        caller=caller_key(request),
    )


# Replace every recovery code. A current authenticator code is required.
@router.post(
    "/me/mfa/recovery-codes",
    response_model=schemas.MfaRecoveryCodesRead,
    responses=error_responses(Unauthenticated, InvalidMfaCode, MfaNotEnrolled, TooManyRequests),
)
async def regenerate_my_recovery_codes(
    request: Request,
    body: schemas.MfaCodeRequest,
    principal: CurrentPrincipal,
    session: Session,
    settings: SettingsDep,
    clock: ClockDep,
) -> schemas.MfaRecoveryCodesRead:
    return await service_mfa.regenerate_recovery_codes(
        session,
        user_id=principal.user_id,
        code=body.code,
        settings=settings,
        now=clock.now(),
        caller=caller_key(request),
    )


# Remove the authenticator. Refused when policy still requires one.
@router.delete(
    "/me/mfa",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(
        Unauthenticated, InvalidMfaCode, MfaNotEnrolled, MfaRequiredByPolicy, TooManyRequests
    ),
)
async def disable_my_mfa(
    request: Request,
    body: schemas.MfaCodeRequest,
    principal: CurrentPrincipal,
    session: Session,
    settings: SettingsDep,
    clock: ClockDep,
) -> Response:
    await service_mfa.disable_for_user(
        session,
        user_id=principal.user_id,
        code=body.code,
        settings=settings,
        now=clock.now(),
        caller=caller_key(request),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
