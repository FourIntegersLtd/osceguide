"""How often one caller may do something.

Two kinds of caller. An address, on the routes where an attacker gains
something by repeating before signing in: signing in, asking for a password
reset, trading a legacy token. And a signed-in person (`per_user`), on the
routes where a bearer token is no brake because each call costs something: a
model call, an email to somebody else, a post everybody reads (E-23). Ordinary
reads and cheap writes are not limited: a bearer token is already a person, and
counting every click would only find the people using the product hardest.

**Mostly it fails open.** An unconfigured or switched-off Redis allows the
call and says so in the log: turning the limiter off is a deployment choice,
and a cache outage must not stop the whole product working. Two exceptions,
for when Redis is reachable but *errors mid-check* — exactly the moment a
password spray would be running (SEC-003): a `fail_closed` limit (password
reset, the second factor) refuses the call, and a `local_fallback` limit
(sign-in) keeps counting in this process instead, so a Redis blip at the start
of an exam neither locks a whole cohort out nor switches the brake off. A limit
was never the only defence; it raises the cost of a spraying run from free to
inconvenient.

The counter is a fixed window rather than a sliding one: two windows'
allowance can land in one burst at the boundary, a distinction no attacker
profits from and a great deal less state to keep.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fastapi import Request

from app.core.auth import CurrentPrincipal
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
    exactly when a spray would be running. `local_fallback` counts in this
    process instead, for a route where refusing everybody is itself the outage
    (sign-in at the start of an exam). A Redis that is switched off or absent
    (`get_redis` returns None) still allows the call — turning the limiter off
    is a deployment choice, not a failure to fail closed against.
    """

    name: str
    allowance: int
    window_seconds: int
    fail_closed: bool = False
    local_fallback: bool = False


# Sign-in is counted twice (S-6). Per account, sized against what a real person
# does: mistyping a password three times in a row is ordinary, ten a minute at
# one account is a guess. Per address, sized for a whole cohort signing in from
# one hospital NAT in the same minute at exam start, which a per-address limit
# of ten used to lock out; it still stops one machine spraying many accounts.
SIGN_IN = Limit(name="sign-in", allowance=10, window_seconds=60, local_fallback=True)
SIGN_IN_ADDRESS = Limit(name="sign-in-address", allowance=300, window_seconds=60, local_fallback=True)
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
# A SAML response posted to the assertion consumer: sized like the SSO
# callback it hands on to, and counted separately so one does not spend the
# other's allowance. The signature is checked by `python3-saml`, so this is not
# guessable either; the limit keeps a forged-response spray from being free.
SAML_ACS = Limit(name="saml-acs", allowance=20, window_seconds=60)
# A CV upload pays for a PDF parse and, behind it, a model call. Five an hour
# is generous for somebody re-uploading a corrected CV and expensive to repeat.
CV_UPLOAD = Limit(name="cv-upload", allowance=5, window_seconds=3600)
# Guessing a six-digit code or a recovery code. Fails closed: a Redis error
# mid-check must not turn the second factor into an unlimited spray.
MFA_VERIFY = Limit(name="mfa-verify", allowance=5, window_seconds=60, fail_closed=True)

# --- per signed-in person (E-23) ----------------------------------------------
#
# Counted by user id, not address: a whole ward behind one NHS proxy is many
# people, and one person on a phone and a laptop is one.

# The default for a write that costs little but should not run in a loop:
# flagging, liking, joining, accepting. A person clicking fast manages one a
# second for a minute; a script manages far more.
USER_WRITE = Limit(name="user-write", allowance=60, window_seconds=60)
# Starts something that pays for a model call or a voice room: an attempt, a
# debrief, a tutor session. Thirty in ten minutes is more stations than anybody
# sits, and a runaway client costs real money every time it loops.
AI_SPEND = Limit(name="ai-spend", allowance=30, window_seconds=600)
# A trial mark of a draft rubric: one full marking call each, and nothing to
# show for it but the preview. Counted per organisation (per person for the
# platform), so a builder pressing "Trial" in a loop cannot spend without end.
TRIAL_MARK = Limit(name="trial-mark", allowance=20, window_seconds=3600)
# Uploading a station document to import: a parse in the request and one or two
# long model calls behind it. Sixty an hour lets an author bring a whole library
# across in a sitting, one file per station, and stops a loop from spending.
STATION_IMPORT = Limit(name="station-import", allowance=60, window_seconds=3600)
# Sends an email to somebody other than the caller: an invitation, a resend, a
# report to support. A bulk upload is one call however many rows it carries;
# the limit is on a loop of calls, which is how an inbox gets flooded.
OUTBOUND_EMAIL = Limit(name="outbound-email", allowance=30, window_seconds=3600)
# Publishes something other people read: a question, a reply, a comment, a
# marketplace slot. Sized well above a busy contributor and well below spam.
PUBLISH = Limit(name="publish", allowance=20, window_seconds=600)


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


def _account_bucket(email: str) -> str:
    """The per-account caller for sign-in: hashed, so no address sits in Redis."""
    normalised = email.strip().lower().encode()
    return "account:" + hashlib.sha256(normalised).hexdigest()[:32]


async def check_sign_in(request: Request, email: str) -> None:
    """Count one sign-in attempt against the account and against the address."""
    await check(SIGN_IN, _account_bucket(email))
    await check(SIGN_IN_ADDRESS, caller_key(request))


# Process-local windows for a `local_fallback` limit while Redis is erroring:
# key -> (window start, calls). Pruned when it grows, so a spray of fresh keys
# cannot grow it without end.
_local_windows: dict[str, tuple[float, int]] = {}
_LOCAL_MAX_KEYS = 10_000


def _count_locally(limit: Limit, key: str) -> None:
    now = time.monotonic()
    if len(_local_windows) > _LOCAL_MAX_KEYS:
        for stale in [k for k, (start, _) in _local_windows.items() if now - start >= limit.window_seconds]:
            del _local_windows[stale]
    start, used = _local_windows.get(key, (now, 0))
    if now - start >= limit.window_seconds:
        start, used = now, 0
    used += 1
    _local_windows[key] = (start, used)
    if used > limit.allowance:
        retry_after = max(int(limit.window_seconds - (now - start)), 1)
        raise TooManyRequests(details={"retry_after": retry_after, "limit": limit.name})


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
        # SEC-003: the credential routes never stop counting. Sign-in counts in
        # this process (refusing everyone would be the outage S-6 describes);
        # a fail-closed limit refuses the call; everything else fails open so a
        # Redis blip does not lock people out of the whole product.
        if limit.local_fallback:
            _count_locally(limit, key)
        elif limit.fail_closed:
            raise TooManyRequests(details={"retry_after": limit.window_seconds, "limit": limit.name}) from exc


def per_user(limit: Limit) -> Callable[..., Awaitable[None]]:
    """A route dependency that counts `limit` against the signed-in caller.

    Used as `dependencies=[Depends(per_user(AI_SPEND))]`, so the handler stays a
    parse-and-call; the route must also declare `TooManyRequests`.
    """

    async def count_this_person(principal: CurrentPrincipal) -> None:
        """Count one call against this person's allowance, or refuse it."""
        await check(limit, f"user:{principal.user_id}")

    return count_this_person
