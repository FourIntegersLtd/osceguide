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
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.errors import Unauthenticated
from app.core.settings import Settings, get_settings

ACCESS_TOKEN_TYPE = "access"  # noqa: S105 - a token kind, not a secret


@dataclass(frozen=True)
class Membership:
    org_id: UUID
    org_slug: str
    role: str
    surface: str | None = None


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    email: str
    memberships: tuple[Membership, ...] = field(default_factory=tuple)
    active_org_slug: str | None = None
    is_platform_admin: bool = False

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
        )
    except (KeyError, ValueError) as exc:
        raise Unauthenticated("Malformed token claims") from exc


_bearer = HTTPBearer(auto_error=False)


async def get_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Principal:
    if credentials is None or not credentials.credentials:
        raise Unauthenticated()
    return decode_access_token(credentials.credentials, settings=settings)


CurrentPrincipal = Annotated[Principal, Depends(get_principal)]


async def require_worker_secret(
    request: Request, settings: Annotated[Settings, Depends(get_settings)]
) -> None:
    """Guard for `/api/worker/*` routes. Fails closed: no configured secret means no access."""
    expected = settings.worker_secret.strip()
    presented = (request.headers.get(settings.worker_secret_header) or "").strip()
    if not expected or not presented or not hmac.compare_digest(expected, presented):
        raise Unauthenticated("Worker authentication failed")
