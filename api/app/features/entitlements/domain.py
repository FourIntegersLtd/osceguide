"""Whether someone may attempt an exam, and why.

One predicate, several sources. A consumer who bought access, a trainee whose institution
granted it, an SSO tenant's member and someone still inside the free trial all reach the same
answer by the same route — what differs is the reason, recorded so "why could they do that?"
stays answerable.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

# Ported verbatim from `b2c/shared/constants/shared_constants.py:89`.
ALLOWED_TRIAL_STATIONS = 3
TRIAL_DAYS = 14

SOURCES = frozenset({"purchase", "org_grant", "trial", "sso_tenant", "admin"})


@dataclass(frozen=True)
class Grant:
    """One grant to attempt an exam, as stored: a source and a window, not yet
    weighed against any particular moment."""

    source: str
    starts_at: datetime
    ends_at: datetime | None = None
    revoked_at: datetime | None = None

    def live_at(self, now: datetime) -> bool:
        """Whether this grant covers `now`: not revoked, already started, and
        not yet ended. A grant that fails this is history, not access."""
        if self.revoked_at is not None:
            return False
        if self.starts_at > now:
            return False
        return self.ends_at is None or self.ends_at > now


@dataclass(frozen=True)
class TrialState:
    """The free-trial counters `trial_available` weighs. Gathered by the
    caller from wherever they actually live (station sets, attempts) since
    this module has no business reading either table."""

    set_station_count: int
    completed_attempt_count: int
    account_created_at: datetime


@dataclass(frozen=True)
class Decision:
    """The allowed/refused verdict `decide` returns, with enough in `source`
    or `reason` that a caller can explain "why" without re-deriving it."""

    allowed: bool
    source: str | None = None
    reason: str | None = None


def trial_available(trial: TrialState, *, now: datetime) -> bool:
    """The legacy free trial rule. Set stations and completed attempts are compared separately
    rather than summed, and the account age comparison is strict, so an account exactly
    fourteen days old still has its trial."""
    if trial.set_station_count >= ALLOWED_TRIAL_STATIONS:
        return False
    if trial.completed_attempt_count >= ALLOWED_TRIAL_STATIONS:
        return False
    return trial.account_created_at >= now - timedelta(days=TRIAL_DAYS)


def decide(
    grants: Sequence[Grant],
    *,
    now: datetime,
    trial: TrialState | None = None,
    exam_code: str | None = None,
) -> Decision:
    """The one question every attempt-creating path asks."""
    live = [grant for grant in grants if grant.live_at(now)]
    if live:
        return Decision(allowed=True, source=live[0].source)

    if trial is not None:
        if trial_available(trial, now=now):
            return Decision(allowed=True, source="trial")
        return Decision(allowed=False, reason="trial_exhausted")

    if grants:
        return Decision(allowed=False, reason="expired")
    return Decision(allowed=False, reason="no_entitlement")
