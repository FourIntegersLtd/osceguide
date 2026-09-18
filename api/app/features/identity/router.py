from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import InvalidInput, Unauthenticated, error_responses
from app.core.memberships import MembershipsFor
from app.core.ports import ClockDep
from app.core.rate_limit import (
    LEGACY_EXCHANGE,
    PASSWORD_RESET,
    SIGN_IN,
    TooManyRequests,
    caller_key,
    check,
)
from app.core.settings import SettingsDep
from app.features.identity import (
    errors,
    schemas,
    service,
    service_legacy,
    service_passwords,
    service_sessions,
)

router = APIRouter(tags=["identity"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.post(
    "/auth/register",
    response_model=schemas.AuthResult,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(errors.EmailTaken, errors.WeakPasswordError),
)
async def register(
    body: schemas.RegisterRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: SettingsDep,
    clock: ClockDep,
) -> schemas.AuthResult:
    return await service.register(
        session,
        email=body.email,
        name=body.name,
        password=body.password,
        settings=settings,
        now=clock.now(),
    )


@router.post(
    "/auth/login",
    response_model=schemas.AuthResult,
    responses=error_responses(errors.InvalidCredentials, errors.AccountSuspended, TooManyRequests),
)
async def login(
    request: Request,
    body: schemas.LoginRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    memberships_for: MembershipsFor,
    settings: SettingsDep,
    clock: ClockDep,
) -> schemas.AuthResult:
    await check(SIGN_IN, caller_key(request))
    return await service_sessions.login_with_memberships(
        session,
        email=body.email,
        password=body.password,
        memberships_for=memberships_for,
        settings=settings,
        now=clock.now(),
    )


@router.post(
    "/auth/refresh",
    response_model=schemas.TokenPair,
    responses=error_responses(errors.InvalidRefreshToken),
)
async def refresh(
    body: schemas.RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    memberships_for: MembershipsFor,
    settings: SettingsDep,
    clock: ClockDep,
) -> schemas.TokenPair:
    return await service_sessions.refresh(
        session,
        refresh_token=body.refresh_token,
        memberships_for=memberships_for,
        settings=settings,
        now=clock.now(),
    )


@router.post(
    "/auth/exchange-legacy",
    response_model=schemas.AuthResult,
    responses=error_responses(
        errors.InvalidLegacyToken,
        errors.LegacyAccountNotImported,
        errors.AccountSuspended,
        errors.LegacyExchangeUnavailable,
        TooManyRequests,
    ),
)
async def exchange_legacy(
    request: Request,
    body: schemas.LegacyExchangeRequest,
    session: Session,
    memberships_for: MembershipsFor,
    settings: SettingsDep,
    clock: ClockDep,
) -> schemas.AuthResult:
    """Sign in here with the session the old backend already gave you."""
    await check(LEGACY_EXCHANGE, caller_key(request))
    return await service_legacy.exchange(
        session,
        provider=body.provider,
        token=body.token,
        memberships_for=memberships_for,
        settings=settings,
        now=clock.now(),
    )


@router.post(
    "/auth/stream-ticket",
    response_model=schemas.StreamTicket,
    responses=error_responses(Unauthenticated),
)
async def mint_stream_ticket(
    principal: CurrentPrincipal,
    settings: SettingsDep,
    clock: ClockDep,
) -> schemas.StreamTicket:
    """A sixty-second credential a browser can put in a stream's URL.

    Minted with an ordinary bearer token, spent immediately on one
    `text/event-stream` connection, and refused by every other route.
    """
    return await service_sessions.mint_stream_ticket(principal, settings=settings, now=clock.now())


@router.post(
    "/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(Unauthenticated),
)
async def logout(
    principal: CurrentPrincipal,
    session: Annotated[AsyncSession, Depends(get_session)],
    clock: ClockDep,
    body: schemas.LogoutRequest | None = None,
) -> Response:
    """Ends the presented session, or every session when none is named."""
    await service_sessions.logout(
        session,
        user_id=principal.user_id,
        refresh_token=body.refresh_token if body else None,
        now=clock.now(),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/auth/password-reset",
    response_model=schemas.Accepted,
    status_code=status.HTTP_202_ACCEPTED,
    # 202 whether or not the address exists, so the only failure is a malformed
    # request. Saying more would turn this into an account-enumeration oracle.
    responses=error_responses(InvalidInput, TooManyRequests),
)
async def begin_password_reset(
    request: Request,
    body: schemas.PasswordResetRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    clock: ClockDep,
) -> schemas.Accepted:
    # Tighter than sign-in: the cost of this request is an email to an inbox
    # the caller chose, which is not theirs.
    await check(PASSWORD_RESET, caller_key(request))
    await service_passwords.begin_password_reset(session, email=body.email, now=clock.now())
    return schemas.Accepted()


@router.post(
    "/auth/password-reset/confirm",
    response_model=schemas.Accepted,
    responses=error_responses(errors.InvalidResetToken, errors.WeakPasswordError),
)
async def confirm_password_reset(
    body: schemas.PasswordResetConfirm,
    session: Annotated[AsyncSession, Depends(get_session)],
    clock: ClockDep,
) -> schemas.Accepted:
    await service_passwords.confirm_password_reset(
        session, token=body.token, password=body.password, now=clock.now()
    )
    return schemas.Accepted()


@router.post(
    "/auth/change-password",
    response_model=schemas.Accepted,
    responses=error_responses(errors.InvalidCredentials, errors.WeakPasswordError),
)
async def change_password(
    body: schemas.ChangePasswordRequest,
    principal: CurrentPrincipal,
    session: Annotated[AsyncSession, Depends(get_session)],
    clock: ClockDep,
) -> schemas.Accepted:
    await service_passwords.change_password(
        session,
        user_id=principal.user_id,
        current=body.current_password,
        new=body.new_password,
        now=clock.now(),
    )
    return schemas.Accepted()


@router.get("/me", response_model=schemas.UserRead, responses=error_responses(Unauthenticated))
async def read_me(
    principal: CurrentPrincipal,
    session: Annotated[AsyncSession, Depends(get_session)],
    memberships_for: MembershipsFor,
) -> schemas.UserRead:
    return await service.read_me(session, principal=principal, memberships_for=memberships_for)
