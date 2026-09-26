"""Authenticating a stream a browser opens.

`EventSource` cannot set an `Authorization` header — the one fetch in the
platform that carries no headers of ours. The two usual answers are both bad:
a session cookie brings CSRF surface to a bearer-only, stateless API, and
`?access_token=` puts a token good for every route into a URL that gets
written to proxy logs, browser history and any CDN in front of the deployment.

So a stream carries a **ticket**: the same claims, a different `typ`, and
sixty seconds to be redeemed. `get_principal` refuses it — only a stream
route accepts one. A caller that can set headers (a test, a worker, a native
client) sends its ordinary bearer token instead and never mints one.

SEC-016: a ticket is redeemable **once**. Each carries a `jti`, and the first
redemption claims it in Redis for the rest of its life; a second presentation
of the same ticket — the replay of one lifted from a proxy log or browser
history — is refused. The guard fails open: when Redis is off (local, or a
deployment that chose to) or unreachable, the ticket still opens its stream,
because a rare, seconds-long reopening of the replay window is a better trade
than dropping every live stream during a cache blip. The ticket's own
sixty-second expiry is the floor either way.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID, uuid4

import jwt
from fastapi import Depends, Header, Query

from app.core.auth import Membership, Principal
from app.core.errors import Unauthenticated
from app.core.logging import get_logger
from app.core.redis import get_redis
from app.core.settings import Settings, get_settings

log = get_logger(__name__)

STREAM_TOKEN_TYPE = "stream"  # noqa: S105 — a token's type claim, not a secret
_REPLAY_PREFIX = "stream-ticket-used"


def issue_stream_ticket(principal: Principal, *, settings: Settings, now: datetime | None = None) -> str:
    """Mint a one-minute, single-use ticket that opens a stream for this principal."""
    issued_at = now or datetime.now(UTC)
    claims: dict[str, Any] = {
        "iss": settings.jwt_issuer,
        "sub": str(principal.user_id),
        "typ": STREAM_TOKEN_TYPE,
        # SEC-016: a per-ticket id, so a redeemed ticket can be remembered and
        # a replay refused.
        "jti": uuid4().hex,
        "iat": int(issued_at.timestamp()),
        "exp": int((issued_at + timedelta(seconds=settings.stream_ticket_ttl_seconds)).timestamp()),
        "email": principal.email,
        "memberships": [
            {
                "org_id": str(membership.org_id),
                "org_slug": membership.org_slug,
                "role": membership.role,
                "surface": membership.surface,
            }
            for membership in principal.memberships
        ],
        "active_org": principal.active_org_slug,
        "platform_admin": principal.is_platform_admin,
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm="HS256")


def _verified_claims(ticket: str, *, settings: Settings) -> dict[str, Any]:
    """Decode and verify a ticket's signature and type, or raise `Unauthenticated`."""
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
    return claims


def _principal_from_claims(claims: dict[str, Any]) -> Principal:
    """Rebuild the principal a ticket's claims describe, or raise `Unauthenticated`."""
    try:
        return Principal(
            user_id=UUID(claims["sub"]),
            email=claims.get("email", ""),
            memberships=tuple(
                Membership(
                    org_id=UUID(entry["org_id"]),
                    org_slug=entry["org_slug"],
                    role=entry["role"],
                    surface=entry.get("surface"),
                )
                for entry in claims.get("memberships", [])
            ),
            active_org_slug=claims.get("active_org"),
            is_platform_admin=bool(claims.get("platform_admin", False)),
        )
    except (KeyError, ValueError) as exc:
        raise Unauthenticated("Malformed ticket claims") from exc


def decode_stream_ticket(ticket: str, *, settings: Settings) -> Principal:
    """Verify a ticket and read who it is for. Does not enforce single use —
    that is `get_stream_principal`'s job, since the replay guard is async."""
    return _principal_from_claims(_verified_claims(ticket, settings=settings))


async def _claim_ticket_or_refuse(claims: dict[str, Any]) -> None:
    """SEC-016: burn this ticket's `jti`, or refuse a replay.

    Fails open (see the module docstring): a ticket with no `jti`, or a Redis
    that is off or erroring, redeems as before — never at the cost of a live
    stream during a cache outage.
    """
    jti = claims.get("jti")
    if not jti:
        return
    client = get_redis()
    if client is None:
        return
    now = int(datetime.now(UTC).timestamp())
    ttl = max(int(claims.get("exp", now)) - now, 1)
    try:
        fresh = await client.set(f"{_REPLAY_PREFIX}:{jti}", "1", nx=True, ex=ttl)
    except Exception as exc:  # noqa: BLE001 - a Redis blip must not drop the stream
        log.warning("stream ticket replay guard unavailable", error=str(exc))
        return
    if not fresh:
        raise Unauthenticated("This stream ticket has already been used")


async def get_stream_principal(
    settings: Annotated[Settings, Depends(get_settings)],
    ticket: Annotated[str | None, Query(description="A stream ticket from POST /auth/stream-ticket")] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> Principal:
    """Who is watching this stream: a ticket in the query, or an ordinary bearer.

    A ticket never reaches `get_principal`, so one leaked from a URL opens a
    stream and nothing else — and only for the minute it lives, and only once
    (SEC-016). A caller that can set headers sends its bearer token instead;
    that token is not single-use, because it never lands in a URL.
    """
    from app.core.auth import decode_access_token  # noqa: PLC0415 - avoids an import cycle

    if ticket:
        claims = _verified_claims(ticket, settings=settings)
        await _claim_ticket_or_refuse(claims)
        return _principal_from_claims(claims)
    if authorization and authorization.lower().startswith("bearer "):
        return decode_access_token(authorization.split(" ", 1)[1], settings=settings)
    raise Unauthenticated("A stream needs a ticket or a bearer token")


StreamPrincipal = Annotated[Principal, Depends(get_stream_principal)]
