"""Error reporting.

`SENTRY_DSN` has been a setting since the first commit and nothing read it,
so a deployed process reported nothing anywhere and looked configured.

Off unless a DSN is set, which keeps local and test runs silent and means a
deployment opts in by configuration rather than by code. Both legacy backends
already report to Sentry, so this is the third of three rather than a new
dependency on a new service.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.core.settings import Settings

log = get_logger(__name__)

# Sampled rather than everything: traces are priced per span and an API that
# the supervisor console polls would otherwise bill for its own heartbeat.
TRACES_SAMPLE_RATE = 0.05


def configure_sentry(settings: Settings) -> bool:
    """Start reporting, if there is somewhere to report to. Returns whether it did."""
    if not settings.sentry_dsn.strip():
        return False
    try:
        import sentry_sdk  # noqa: PLC0415 - optional at runtime, and only here
    except ImportError:
        log.warning("SENTRY_DSN is set but sentry-sdk is not installed")
        return False

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env.value,
        traces_sample_rate=TRACES_SAMPLE_RATE,
        # The request body can hold a password, a legacy token or a whole
        # transcript. None of that belongs in an error report, and the default
        # is to send it.
        send_default_pii=False,
        max_request_body_size="never",
    )
    return True
