"""Error reporting.

Off unless `SENTRY_DSN` is set, which keeps local and test runs silent and
means a deployment opts in by configuration rather than by code.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError

from app.core.logging import get_logger
from app.core.settings import Settings

log = get_logger(__name__)

POOL_EXHAUSTED_TAG = "db.pool_exhausted"


def tag_pool_exhaustion(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any]:
    """Mark an error report caused by waiting too long for a pooled connection.

    The pool's timeout is the first visible sign that the database line is the
    bottleneck on an exam day; tagged, one Sentry search finds every one.
    """
    exc_info = hint.get("exc_info")
    if exc_info and isinstance(exc_info[1], SQLAlchemyTimeoutError):
        event.setdefault("tags", {})[POOL_EXHAUSTED_TAG] = "true"
    return event


def configure_sentry(settings: Settings) -> bool:
    """Start reporting, if there is somewhere to report to. Returns whether it did."""
    if not settings.sentry_dsn.strip():
        return False
    try:
        import sentry_sdk  # optional at runtime, and only here
    except ImportError:
        log.warning("SENTRY_DSN is set but sentry-sdk is not installed")
        return False

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env.value,
        # Sampled, not everything: traces are priced per span and the console's own heartbeat
        # would otherwise bill for itself. A setting, so a load test can raise it.
        traces_sample_rate=settings.sentry_traces_sample_rate,
        before_send=tag_pool_exhaustion,  # type: ignore[arg-type]
        # The request body can hold a password, a legacy token or a whole
        # transcript. None of that belongs in an error report, and the default
        # is to send it.
        send_default_pii=False,
        max_request_body_size="never",
    )
    return True


def report_message(message: str, *, level: str = "error") -> bool:
    """Send one message to Sentry, so a condition no exception carries still reaches a person.

    Returns whether it was handed to the SDK; with no DSN configured the SDK drops it.
    """
    try:
        import sentry_sdk
    except ImportError:
        log.warning("sentry-sdk is not installed; message not reported", message=message)
        return False
    sentry_sdk.capture_message(message, level=level)  # type: ignore[arg-type]
    return True
