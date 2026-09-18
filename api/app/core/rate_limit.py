"""How often one caller may do something.

Only on the routes where an attacker gains something by repeating: signing
in, asking for a password reset, and trading a legacy token. Everything else
is behind a bearer token already, and a limiter in front of the whole API
would mostly rate-limit the supervisor console polling itself.

**It fails open.** A Redis outage must not stop people signing in — that
turns a cache problem into an outage of the product — so an unreachable or
unconfigured Redis allows the call and says so in the log. That is the right
trade for this particular defence: it raises the cost of a password-spraying
run from free to inconvenient, and it was never the only thing standing
between an attacker and an account. Where the answer must be no when the
check cannot run, we fail closed instead, as `require_worker_secret` does.

The counter is a fixed window rather than a sliding one: two windows'
allowance can land in one burst at the boundary, which for "five password
resets a minute" is a distinction no attacker profits from and a great deal
less state to keep.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from app.core.errors import AppError
from app.core.logging import get_logger
from app.core.redis import get_redis

log = get_logger(__name__)

KEY_PREFIX = "ratelimit"


class TooManyRequests(AppError):
    """429. Carries `retry_after` so a client can wait rather than hammer."""

    status = 429
    code = "too_many_requests"
    default_message = "Too many attempts. Wait a moment and try again."


@dataclass(frozen=True)
class Limit:
    """`allowance` calls per `window_seconds`, per caller."""

    name: str
    allowance: int
    window_seconds: int


# Sized against what a real person does, not what feels safe. Somebody
# mistyping a password three times in a row is ordinary; thirty attempts a
# minute from one address is not a person.
SIGN_IN = Limit(name="sign-in", allowance=10, window_seconds=60)
# Deliberately tighter, because the cost of the request is an email to
# somebody else's inbox: the address is the attacker's choice, not theirs.
PASSWORD_RESET = Limit(name="password-reset", allowance=5, window_seconds=300)
# A legacy token is signed and verifiable, so this is not guessable the way a
# password is; the limit is here because the route reaches the user table.
LEGACY_EXCHANGE = Limit(name="legacy-exchange", allowance=20, window_seconds=60)


def caller_key(request: Request) -> str:
    """Who is being counted.

    The client address, taken from the proxy header when one is set, because
    the platform sits behind one and every caller would otherwise share the
    load balancer's address and exhaust one bucket between them. Spoofable by
    anyone who can set the header directly; that is why this raises the cost
    of an attack rather than preventing one.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
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
    except Exception as exc:  # noqa: BLE001 - any Redis failure allows the call
        log.warning("rate limit unavailable", limit=limit.name, error=str(exc))
