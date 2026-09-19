from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import Forbidden, Unauthenticated, error_responses
from app.core.tenancy import PlatformAdmin
from app.features.sso import errors, schemas, service

router = APIRouter(tags=["sso"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/auth/sso/sign-in",
    response_model=schemas.SsoSignIn,
    responses=error_responses(errors.SsoNotConfigured, errors.InvalidSsoBinding),
)
async def read_sign_in(
    session: Session,
    host: Annotated[
        str | None,
        Query(description="The hostname the visitor arrived at, for a white-label site."),
    ] = None,
    email: Annotated[
        str | None,
        Query(description="An address typed into the ordinary sign-in form."),
    ] = None,
) -> schemas.SsoSignIn:
    """Whether this visitor's organisation signs in somewhere else.

    **Unauthenticated, and it has to be**: this is what a sign-in page asks
    before anybody has signed in. The retiring client answered it from a
    hostname allow-list compiled into the bundle, so adding a partner meant a
    frontend deploy and the tenant slug, the button's wording and the
    "no password form" rule were three things that could disagree with the
    backend.

    A 404 means "sign in here, with a password", which is the ordinary case and
    what every host that is not a partner's gets.
    """
    if host:
        return await service.sign_in_for_host(session, host)
    if email:
        return await service.sign_in_for_email(session, email)
    raise errors.InvalidSsoBinding("Give either a host or an email address.")


@router.get(
    "/platform/orgs/{org_slug}/sso",
    response_model=schemas.SsoConfigRead,
    responses=error_responses(Unauthenticated, Forbidden, errors.SsoNotConfigured),
)
async def read_config(org_slug: str, _admin: PlatformAdmin, session: Session) -> schemas.SsoConfigRead:
    """The whole arrangement, including the issuer and every binding."""
    return await service.read_config(session, org_slug)


@router.put(
    "/platform/orgs/{org_slug}/sso",
    response_model=schemas.SsoConfigRead,
    responses=error_responses(
        Unauthenticated,
        Forbidden,
        errors.SsoNotConfigured,
        errors.UnknownSsoProvider,
        errors.InvalidSsoBinding,
        errors.SsoNotConfigurableError,
        errors.SsoBindingTaken,
    ),
)
async def save_config(
    org_slug: str,
    body: schemas.SaveSsoConfig,
    _admin: PlatformAdmin,
    session: Session,
) -> schemas.SsoConfigRead:
    """Write it. Platform admin only, deliberately.

    Whoever controls the issuer controls who may sign in as that institution's
    members, so this is not a field to put on a customer's own settings screen
    beside their logo. When there is an onboarding flow with a domain
    verification step in it, that is where this moves.
    """
    return await service.save_config(session, org_slug, body)
