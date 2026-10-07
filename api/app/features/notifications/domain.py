"""When queued mail goes out, and when to give up.

Messages are rows written by whatever slice needed them, in the transaction that
justified them. This decides only when to attempt one and how long to wait after
a failure.
"""

from __future__ import annotations

from datetime import datetime, timedelta

# Twelve tries span about five hours (30s doubling to the one-hour cap). Six
# gave up after a quarter of an hour, so any provider outage longer than a
# coffee break lost every invitation, reset and receipt queued during it.
MAX_ATTEMPTS = 12
# How long a claimed message may stay claimed before another worker may take
# it. Comfortably longer than any send should take, so a slow provider is not
# mistaken for a dead worker.
CLAIM_TIMEOUT_SECONDS = 600
MAX_RETRY_SECONDS = 3600
BASE_RETRY_SECONDS = 30


def retry_delay(attempt: int) -> int:
    """Exponential, capped.

    A provider that is refusing is usually refusing for a while, and hammering
    it makes delivery worse for every other message in the queue.
    """
    return int(min(MAX_RETRY_SECONDS, BASE_RETRY_SECONDS * (2 ** max(0, attempt - 1))))


def should_retry(*, attempts: int) -> bool:
    """After enough tries a message is abandoned rather than retried forever.

    A queue that never gives up hides the fact that something needs a person.
    An abandoned message is not lost: the console's System health page lists it
    and sends it again (`service.retry_undelivered`).
    """
    return attempts < MAX_ATTEMPTS


def next_available(*, attempts: int, now: datetime) -> datetime:
    return now + timedelta(seconds=retry_delay(attempts))


def stale_claim_cutoff(now: datetime) -> datetime:
    """Claims older than this belong to a worker that is not coming back."""
    return now - timedelta(seconds=CLAIM_TIMEOUT_SECONDS)
