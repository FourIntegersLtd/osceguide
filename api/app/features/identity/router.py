"""Registration, sign-in, refresh, logout and the password-reset flow."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status

from app.core.auth import CurrentPrincipal
from app.core.db import SessionDep
from app.core.db import SessionDep as Session
from app.core.errors import InvalidInput, Unauthenticated, error_responses
from app.core.memberships import MembershipsFor
from app.core.ports import ClockDep
from app.core.rate_limit import (
    INVITATION_LOOKUP,
    LEGACY_EXCHANGE,
    PASSWORD_RESET,
    REGISTER,
    USER_WRITE,
    TooManyRequests,
    caller_key,
    check,
    check_sign_in,
    per_user,
)
from app.core.settings import SettingsDep
from app.features.identity import (
    errors,
    schemas,
    service,
    service_email_change,
    service_legacy,
    service_mfa,
    service_passwords,
    service_sessions,
)

router = APIRouter(tags=["identity"])


# Create the account and sign them in immediately: registering is also the
# first login, so there is no separate first-session step.
@router.post(
    "/auth/register",
    response_model=schemas.SignInResult,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(errors.EmailTaken, errors.WeakPasswordError, TooManyRequests),
)
async def register(
    request: Request,
    body: schemas.RegisterRequest,
    session: SessionDep,
    settings: SettingsDep,
    clock: ClockDep,
) -> schemas.SignInResult:
    # SEC-004: unauthenticated and it writes a user + sends mail, so it is
    # rate limited like the other public identity routes.
    await check(REGISTER, caller_key(request))
    return await service.register(
        session,
        email=body.email,
        name=body.name,
        password=body.password,
        settings=settings,
        now=clock.now(),
        exam_code=body.exam_code,
    )


# The ordinary password sign-in, refused for an account an SSO-only
# arrangement has switched to signing in elsewhere.
@router.post(
    "/auth/login",
    response_model=schemas.SignInResult,
    responses=error_responses(
        errors.InvalidCredentials, errors.AccountSuspended, errors.PasswordLoginDisabled, TooManyRequests
    ),
)
async def login(
    request: Request,
    body: schemas.LoginRequest,
    session: SessionDep,
    memberships_for: MembershipsFor,
    settings: SettingsDep,
    clock: ClockDep,
) -> schemas.SignInResult:
    await check_sign_in(request, body.email)
    return await service_sessions.login_with_memberships(
        session,
        email=body.email,
        password=body.password,
        memberships_for=memberships_for,
        settings=settings,
        now=clock.now(),
    )


# Trade a refresh token for a new access/refresh pair, rotating the chain;
# presenting one already spent revokes the whole chain rather than just
# refusing the one request, since that shape means the token leaked.
@router.post(
    "/auth/refresh",
    response_model=schemas.TokenPair,
    responses=error_responses(errors.InvalidRefreshToken),
)
async def refresh(
    body: schemas.RefreshRequest,
    session: SessionDep,
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
    response_model=schemas.SignInResult,
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
) -> schemas.SignInResult:
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
    session: SessionDep,
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


# Always 202, whether or not the address has an account: telling the two
# apart would make this an account-enumeration oracle.
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
    session: SessionDep,
    clock: ClockDep,
) -> schemas.Accepted:
    # Tighter than sign-in: the cost of this request is an email to an inbox
    # the caller chose, which is not theirs.
    await check(PASSWORD_RESET, caller_key(request))
    await service_passwords.begin_password_reset(session, email=body.email, now=clock.now())
    return schemas.Accepted()


# Who sent an invitation, for the accept page to greet the person with. The token is the only
# credential and only the organisation's name comes back; every other token gets the same refusal
# `password-reset/confirm` gives, so this cannot tell a tester which guesses were real.
@router.get(
    "/auth/invitation/{token}",
    response_model=schemas.InvitationLookup,
    responses=error_responses(errors.InvalidResetToken, TooManyRequests),
)
async def look_up_invitation(
    request: Request, token: str, session: SessionDep, clock: ClockDep
) -> schemas.InvitationLookup:
    await check(INVITATION_LOOKUP, caller_key(request))
    name = await service_passwords.invitation_organisation_name(session, token=token, now=clock.now())
    return schemas.InvitationLookup(organisation_name=name)


# Redeem a reset token for a new password. Ends every existing session, the
# same as a password change: a reset is itself a sign of possible compromise.
@router.post(
    "/auth/password-reset/confirm",
    response_model=schemas.PasswordResetDone,
    responses=error_responses(errors.InvalidResetToken, errors.WeakPasswordError, TooManyRequests),
)
async def confirm_password_reset(
    request: Request,
    body: schemas.PasswordResetConfirm,
    session: SessionDep,
    clock: ClockDep,
) -> schemas.PasswordResetDone:
    # SEC-004: the token is high-entropy, but this caps a brute-force attempt at
    # guessing one rather than leaving the only limit its length.
    await check(PASSWORD_RESET, caller_key(request))
    email = await service_passwords.confirm_password_reset(
        session, token=body.token, password=body.password, now=clock.now()
    )
    return schemas.PasswordResetDone(email=email)


# Change the password when the current one still works. Ends every session,
# so a stolen credential does not survive the owner locking it out, and
# answers with a fresh pair for the device that made the change.
@router.post(
    "/auth/change-password",
    response_model=schemas.TokenPair,
    responses=error_responses(
        errors.AccountNotFound,
        errors.InvalidCredentials,
        errors.WeakPasswordError,
        errors.PasswordLoginDisabled,
        errors.PasswordNotSet,
        errors.AccountSuspended,
    ),
)
async def change_password(
    body: schemas.ChangePasswordRequest,
    principal: CurrentPrincipal,
    session: SessionDep,
    memberships_for: MembershipsFor,
    settings: SettingsDep,
    clock: ClockDep,
) -> schemas.TokenPair:
    return await service_passwords.change_password(
        session,
        user_id=principal.user_id,
        current=body.current_password,
        new=body.new_password,
        memberships_for=memberships_for,
        settings=settings,
        now=clock.now(),
    )


# Mail a confirmation link to a new address. Always 202 once the password is right, whether or not
# the address is already held, so the form tells nobody who has an account.
@router.post(
    "/me/email-change",
    response_model=schemas.Accepted,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(
        errors.AccountNotFound,
        errors.InvalidCredentials,
        errors.PasswordLoginDisabled,
        errors.PasswordNotSet,
        errors.AccountSuspended,
        TooManyRequests,
    ),
    dependencies=[Depends(per_user(USER_WRITE))],
)
async def begin_email_change(
    body: schemas.EmailChangeRequest,
    principal: CurrentPrincipal,
    session: SessionDep,
    settings: SettingsDep,
    clock: ClockDep,
) -> schemas.Accepted:
    await service_email_change.begin_email_change(
        session,
        user_id=principal.user_id,
        new_email=body.new_email,
        current_password=body.current_password,
        settings=settings,
        now=clock.now(),
    )
    return schemas.Accepted()


# Use the link mailed to the new address. Public: the link is the proof, and it is opened from an
# inbox that may not be signed in. Ends every session, since the address is how the account is known.
@router.post(
    "/auth/email-change/confirm",
    response_model=schemas.EmailChanged,
    responses=error_responses(errors.InvalidEmailChangeToken, TooManyRequests),
)
async def confirm_email_change(
    request: Request,
    body: schemas.EmailChangeConfirm,
    session: SessionDep,
    settings: SettingsDep,
    clock: ClockDep,
) -> schemas.EmailChanged:
    await check(PASSWORD_RESET, caller_key(request))
    email = await service_email_change.confirm_email_change(
        session, token=body.token, settings=settings, now=clock.now()
    )
    return schemas.EmailChanged(email=email)


# Redeem a sign-in challenge with an authenticator code or a one-time recovery code.
@router.post(
    "/auth/mfa/verify",
    response_model=schemas.AuthResult,
    responses=error_responses(
        errors.InvalidMfaCode,
        errors.MfaChallengeExpired,
        errors.MfaNotEnrolled,
        errors.PasswordLoginDisabled,
        TooManyRequests,
    ),
)
async def verify_mfa(
    request: Request,
    body: schemas.MfaVerifyRequest,
    session: Session,
    memberships_for: MembershipsFor,
    settings: SettingsDep,
    clock: ClockDep,
) -> schemas.AuthResult:
    return await service_mfa.verify_challenge(
        session,
        challenge_token=body.challenge_token,
        code=body.code,
        recovery_code=body.recovery_code,
        memberships_for=memberships_for,
        settings=settings,
        now=clock.now(),
        caller=caller_key(request),
    )


# Start authenticator enrolment when sign-in said a second factor is required.
@router.post(
    "/auth/mfa/enrol/start",
    response_model=schemas.MfaEnrolmentStart,
    responses=error_responses(
        errors.MfaChallengeExpired, errors.MfaAlreadyEnrolled, errors.PasswordLoginDisabled
    ),
)
async def start_mfa_enrolment(
    body: schemas.MfaEnrolStartRequest,
    session: Session,
    settings: SettingsDep,
    clock: ClockDep,
) -> schemas.MfaEnrolmentStart:
    return await service_mfa.start_enrolment_from_challenge(
        session, challenge_token=body.challenge_token, settings=settings, now=clock.now()
    )


# Confirm that authenticator and sign in. Recovery codes are in this response only.
@router.post(
    "/auth/mfa/enrol/confirm",
    response_model=schemas.MfaEnrolmentConfirmed,
    responses=error_responses(
        errors.InvalidMfaCode,
        errors.MfaChallengeExpired,
        errors.MfaNotEnrolled,
        errors.MfaAlreadyEnrolled,
        errors.PasswordLoginDisabled,
        TooManyRequests,
    ),
)
async def confirm_mfa_enrolment(
    request: Request,
    body: schemas.MfaEnrolConfirmRequest,
    session: Session,
    memberships_for: MembershipsFor,
    settings: SettingsDep,
    clock: ClockDep,
) -> schemas.MfaEnrolmentConfirmed:
    return await service_mfa.confirm_enrolment_from_challenge(
        session,
        challenge_token=body.challenge_token,
        code=body.code,
        memberships_for=memberships_for,
        settings=settings,
        now=clock.now(),
        caller=caller_key(request),
    )
