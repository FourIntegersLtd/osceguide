"""Who is calling.

Two kinds of caller exist:

- A **principal**: a user carrying a platform-issued JWT. The token holds the
  user's memberships and the workspace they are acting in, so a request never
  needs a database round-trip just to know who is asking.
- A **worker**: a LiveKit worker process presenting the shared worker secret.

Issuing tokens (login, refresh, workspace switch) lives in the `identity`
slice. This module only knows how to read and verify them.
"""

from __future__ import annotations

import hmac
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

import jwt
from fastapi import Depends, Request
from fastapi.routing import APIRoute
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.errors import Forbidden, Unauthenticated
from app.core.settings import Settings, get_settings

ACCESS_TOKEN_TYPE = "access"  # noqa: S105 — the token's type claim, not a secret


@dataclass(frozen=True)
class Membership:
    org_id: UUID
    org_slug: str
    role: str
    surface: str | None = None
    # Display only, and deliberately not a token claim: authorisation never
    # reads it, and a renamed organisation would otherwise show its old name
    # for the life of every token already issued. Filled by the tenancy lookup.
    org_name: str | None = None
    # Also display only, and for the same reason. The frontend picks which
    # workspace shell to render from this — an institution examines a cohort, a
    # partner watches a funnel — and that is a presentation choice, never an
    # authorisation one. Baking it into a claim would freeze it for fifteen
    # minutes after an organisation changed what it is.
    org_type: str | None = None


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    email: str
    memberships: tuple[Membership, ...] = field(default_factory=tuple)
    active_org_slug: str | None = None
    is_platform_admin: bool = False
    # Someone provisioned with a temporary password. Carried in the token
    # because a password change revokes every refresh chain, so the next token
    # they hold is minted fresh with this cleared.
    must_change_password: bool = False

    def membership_for(self, org_slug: str) -> Membership | None:
        return next((m for m in self.memberships if m.org_slug == org_slug), None)

    @property
    def active_membership(self) -> Membership | None:
        return self.membership_for(self.active_org_slug) if self.active_org_slug else None


def issue_access_token(principal: Principal, *, settings: Settings, now: datetime | None = None) -> str:
    issued_at = now or datetime.now(UTC)
    claims: dict[str, Any] = {
        "iss": settings.jwt_issuer,
        "sub": str(principal.user_id),
        "typ": ACCESS_TOKEN_TYPE,
        "iat": int(issued_at.timestamp()),
        "exp": int((issued_at + timedelta(seconds=settings.jwt_access_ttl_seconds)).timestamp()),
        "email": principal.email,
        "memberships": [
            {"org_id": str(m.org_id), "org_slug": m.org_slug, "role": m.role, "surface": m.surface}
            for m in principal.memberships
        ],
        "active_org": principal.active_org_slug,
        "platform_admin": principal.is_platform_admin,
        "must_change_password": principal.must_change_password,
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str, *, settings: Settings) -> Principal:
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise Unauthenticated("Invalid or expired token") from exc
    if claims.get("typ") != ACCESS_TOKEN_TYPE:
        raise Unauthenticated("Wrong token type")
    try:
        memberships = tuple(
            Membership(
                org_id=UUID(m["org_id"]), org_slug=m["org_slug"], role=m["role"], surface=m.get("surface")
            )
            for m in claims.get("memberships", [])
        )
        return Principal(
            user_id=UUID(claims["sub"]),
            email=claims.get("email", ""),
            memberships=memberships,
            active_org_slug=claims.get("active_org"),
            is_platform_admin=bool(claims.get("platform_admin", False)),
            must_change_password=bool(claims.get("must_change_password", False)),
        )
    except (KeyError, ValueError) as exc:
        raise Unauthenticated("Malformed token claims") from exc


_bearer = HTTPBearer(auto_error=False)


# Whether a principal holding a temporary password may call a given operation.
# The rule belongs to `identity`; the enforcement point belongs to core, so
# they meet at a seam `main.py` ties together, like the org policies.
_password_gate: list[Callable[[str], bool]] = []


def bind_password_gate(may_call: Callable[[str], bool]) -> None:
    _password_gate.clear()
    _password_gate.append(may_call)


class PasswordChangeRequired(Forbidden):
    """A temporary password reaches only the routes that let you replace it.

    Its own code, because the client's response is a redirect to the
    change-password screen rather than "you lack permission".
    """

    code = "password_change_required"
    default_message = "Set a new password before continuing"


async def get_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Principal:
    if credentials is None or not credentials.credentials:
        raise Unauthenticated()
    principal = decode_access_token(credentials.credentials, settings=settings)
    if principal.must_change_password:
        _refuse_unless_password_route(request)
    return principal


def _refuse_unless_password_route(request: Request) -> None:
    """Enforce `identity.domain.may_call`.

    The rule was written, unit-tested, documented in the slice README and never
    called: a user provisioned with a temporary password could reach every
    route in the API. Enforced here rather than per-router because "every route
    except these" is not something fifty routers can be trusted to remember.
    """
    from app.core.openapi import operation_id  # noqa: PLC0415 - avoids an import cycle

    if not _password_gate:
        raise RuntimeError("No password gate bound. app.main.create_app must call bind_password_gate.")
    route = request.scope.get("route")
    name = operation_id(route) if isinstance(route, APIRoute) else ""
    if not _password_gate[0](name):
        raise PasswordChangeRequired()


CurrentPrincipal = Annotated[Principal, Depends(get_principal)]


async def get_principal_if_present(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Principal | None:
    """Whoever is calling, or nobody.

    For the handful of reads that are genuinely public but answer differently
    to somebody signed in — a published article is readable by a visitor, and
    its unpublished draft is readable by the admin writing it.

    A *bad* token is still a refusal. "No credentials" and "credentials that do
    not decode" are different: treating the second as anonymous would turn an
    expired session into a silent downgrade, and the caller would see a public
    answer where they expected theirs.
    """
    if credentials is None or not credentials.credentials:
        return None
    principal = decode_access_token(credentials.credentials, settings=settings)
    if principal.must_change_password:
        _refuse_unless_password_route(request)
    return principal


MaybePrincipal = Annotated[Principal | None, Depends(get_principal_if_present)]


async def require_worker_secret(
    request: Request, settings: Annotated[Settings, Depends(get_settings)]
) -> None:
    """Guard for `/api/worker/*` routes. Fails closed: no configured secret means no access."""
    expected = settings.worker_secret.strip()
    presented = (request.headers.get(settings.worker_secret_header) or "").strip()
    if not expected or not presented or not hmac.compare_digest(expected, presented):
        raise Unauthenticated("Worker authentication failed")
