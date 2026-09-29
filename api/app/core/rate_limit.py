"""How often one caller may do something.

Only on the routes where an attacker gains something by repeating: signing
in, asking for a password reset, and trading a legacy token. Everything else
is behind a bearer token already.

**Mostly it fails open.** An unconfigured or switched-off Redis allows the
call and says so in the log: turning the limiter off is a deployment choice,
and a cache outage must not stop the whole product working. The exception is a
`fail_closed` limit — the credential routes — which refuses the call when
Redis is reachable but *errors mid-check*, since that is exactly the moment a
password spray would be running (SEC-003). A limit was never the only defence;
it raises the cost of a spraying run from free to inconvenient.

The counter is a fixed window rather than a sliding one: two windows'
allowance can land in one burst at the boundary, a distinction no attacker
profits from and a great deal less state to keep.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from app.core.errors import AppError
from app.core.logging import get_logger
from app.core.redis import get_redis
from app.core.settings import get_settings

log = get_logger(__name__)

KEY_PREFIX = "ratelimit"


class TooManyRequests(AppError):
    """429. Carries `retry_after` so a client can wait rather than hammer."""

    status = 429
    code = "too_many_requests"
    default_message = "Too many attempts. Wait a moment and try again."


@dataclass(frozen=True)
class Limit:
    """`allowance` calls per `window_seconds`, per caller.

    `fail_closed` decides what happens when Redis is *reachable but errors* mid
    check: a credential-guessing route (sign-in, password reset) refuses the
    call rather than let the limiter silently switch off under load, which is
    exactly when a spray would be running. A Redis that is switched off or
    absent (`get_redis` returns None) still allows the call — turning the
    limiter off is a deployment choice, not a failure to fail closed against.
    """

    name: str
    allowance: int
    window_seconds: int
    fail_closed: bool = False


# Sized against what a real person does, not what feels safe. Somebody
# mistyping a password three times in a row is ordinary; thirty attempts a
# minute from one address is not a person.
SIGN_IN = Limit(name="sign-in", allowance=10, window_seconds=60, fail_closed=True)
# Deliberately tighter, because the cost of the request is an email to
# somebody else's inbox: the address is the attacker's choice, not theirs.
PASSWORD_RESET = Limit(name="password-reset", allowance=5, window_seconds=300, fail_closed=True)
# SEC-004: registration reaches the user table and sends a welcome email, and
# it is unauthenticated. Sized like sign-in — a person makes one account, not ten.
REGISTER = Limit(name="register", allowance=10, window_seconds=60)
# A legacy token is signed and verifiable, so this is not guessable the way a
# password is; the limit is here because the route reaches the user table.
LEGACY_EXCHANGE = Limit(name="legacy-exchange", allowance=20, window_seconds=60)
# An SSO callback reaches the broker and the user table, and provisions an
# account on first sign-in. The token is verified by the broker, so this is not
# guessable either; the limit keeps a forged-token spray from being free.
SSO_CALLBACK = Limit(name="sso-callback", allowance=20, window_seconds=60)
# A CV upload pays for a PDF parse and, behind it, a model call. Five an hour
# is generous for somebody re-uploading a corrected CV and expensive to repeat.
CV_UPLOAD = Limit(name="cv-upload", allowance=5, window_seconds=3600)
# Guessing a six-digit code or a recovery code. Fails closed: a Redis error
# mid-check must not turn the second factor into an unlimited spray.
MFA_VERIFY = Limit(name="mfa-verify", allowance=5, window_seconds=60, fail_closed=True)


def caller_key(request: Request) -> str:
    """Who is being counted.

    SEC-003: `X-Forwarded-For` is `client, proxy1, …, ourproxy`, each hop
    appending the address it saw. The leftmost entry is written by the caller
    and can say anything, so counting by it lets an attacker mint a fresh
    bucket per forged address and never hit the limit. We count instead by the
    entry `trusted_proxy_hops` from the right — the address *our own* proxy
    observed, which the caller cannot forge past. With no proxy in front (the
    header absent) this is the socket peer.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        parts = [part.strip() for part in forwarded.split(",") if part.strip()]
        if parts:
            hops = max(get_settings().trusted_proxy_hops, 1)
            # `parts[-hops]` when the chain is long enough; otherwise the
            # leftmost, which is as far back as the header reaches.
            index = -hops if hops <= len(parts) else 0
            return parts[index]
    client = request.client
    return client.host if client else "unknown"


async def check(limit: Limit, caller: str) -> None:
    """Count this call, and refuse it if the window is full."""
    client = get_redis()
    if client is None:
        return
    key = f"{KEY_PREFIX}:{limit.name}:{caller}"
    try:
        used = await client.incr(key)
        if used == 1:
            # Only the first call in a window sets the expiry, so a burst
            # cannot keep pushing the window out in front of itself.
            await client.expire(key, limit.window_seconds)
        if used > limit.allowance:
            ttl = await client.ttl(key)
            raise TooManyRequests(details={"retry_after": max(ttl, 1), "limit": limit.name})
    except TooManyRequests:
        raise
    except Exception as exc:  # noqa: BLE001 - a Redis failure mid-check
        log.warning("rate limit unavailable", limit=limit.name, error=str(exc))
        # SEC-003: a fail-closed limit (the credential routes) refuses the call
        # when the counter cannot be trusted; everything else keeps failing open
        # so a Redis blip does not lock people out of the whole product.
        if limit.fail_closed:
            raise TooManyRequests(details={"retry_after": limit.window_seconds, "limit": limit.name}) from exc
