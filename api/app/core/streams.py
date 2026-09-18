"""Authenticating a stream a browser opens.

`EventSource` cannot set an `Authorization` header — it is the one fetch in the
platform that carries no headers of ours. The two usual answers are both bad:

- **A cookie**, which is what b2c does (`withCredentials: true`). This API is
  bearer-only and stateless by design; adding a session cookie to serve one
  route would bring CSRF surface with it.
- **`?access_token=`**, which puts a fifteen-minute token good for every route
  in the API into a URL, and URLs are written to proxy logs, browser history
  and any CDN in front of the deployment.

So a stream carries a **ticket**: the same claims, a different `typ`, and sixty
seconds to be redeemed. `get_principal` refuses it — only a stream route
accepts one — and it is worthless by the time a log is read. A caller that can
set headers (a test, a worker, a native client) sends its ordinary bearer token
instead and never mints one.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

import jwt
from fastapi import Depends, Header, Query

from app.core.auth import Membership, Principal
from app.core.errors import Unauthenticated
from app.core.settings import Settings, get_settings

STREAM_TOKEN_TYPE = "stream"  # noqa: S105 — a token's type claim, not a secret


def issue_stream_ticket(principal: Principal, *, settings: Settings, now: datetime | None = None) -> str:
    issued_at = now or datetime.now(UTC)
    claims: dict[str, Any] = {
        "iss": settings.jwt_issuer,
        "sub": str(principal.user_id),
        "typ": STREAM_TOKEN_TYPE,
        "iat": int(issued_at.timestamp()),
        "exp": int((issued_at + timedelta(seconds=settings.stream_ticket_ttl_seconds)).timestamp()),
        "email": principal.email,
        "memberships": [
            {"org_id": str(m.org_id), "org_slug": m.org_slug, "role": m.role, "surface": m.surface}
            for m in principal.memberships
        ],
        "active_org": principal.active_org_slug,
        "platform_admin": principal.is_platform_admin,
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm="HS256")


def decode_stream_ticket(ticket: str, *, settings: Settings) -> Principal:
    try:
        claims = jwt.decode(
            ticket,
            settings.jwt_secret,
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise Unauthenticated("Invalid or expired stream ticket") from exc
    if claims.get("typ") != STREAM_TOKEN_TYPE:
        raise Unauthenticated("Wrong token type")
    try:
        return Principal(
            user_id=UUID(claims["sub"]),
            email=claims.get("email", ""),
            memberships=tuple(
                Membership(
                    org_id=UUID(m["org_id"]),
                    org_slug=m["org_slug"],
                    role=m["role"],
                    surface=m.get("surface"),
                )
                for m in claims.get("memberships", [])
            ),
            active_org_slug=claims.get("active_org"),
            is_platform_admin=bool(claims.get("platform_admin", False)),
        )
    except (KeyError, ValueError) as exc:
        raise Unauthenticated("Malformed ticket claims") from exc


async def get_stream_principal(
    settings: Annotated[Settings, Depends(get_settings)],
    ticket: Annotated[str | None, Query(description="A stream ticket from POST /auth/stream-ticket")] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> Principal:
    """Who is watching this stream: a ticket in the query, or an ordinary bearer.

    A ticket never reaches `get_principal`, so one leaked from a URL opens a
    stream and nothing else — and only for the minute it lives.
    """
    from app.core.auth import decode_access_token  # noqa: PLC0415 - avoids an import cycle

    if ticket:
        return decode_stream_ticket(ticket, settings=settings)
    if authorization and authorization.lower().startswith("bearer "):
        return decode_access_token(authorization.split(" ", 1)[1], settings=settings)
    raise Unauthenticated("A stream needs a ticket or a bearer token")


StreamPrincipal = Annotated[Principal, Depends(get_stream_principal)]
