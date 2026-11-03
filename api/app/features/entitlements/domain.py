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
# Each trial station may be sat this many times, matching the mock's per-station limit.
TRIAL_ATTEMPTS_PER_STATION = 3

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
    completed_station_count: int
    # When the free trial began (see identity `UserRef.trial_started_at`).
    trial_started_at: datetime
    # The station being started, when it is already one of this person's trial stations:
    # how many times they have finished it. None for a station they have not started yet.
    completed_on_this_station: int | None = None


@dataclass(frozen=True)
class Decision:
    """The allowed/refused verdict `decide` returns, with enough in `source`
    or `reason` that a caller can explain "why" without re-deriving it."""

    allowed: bool
    source: str | None = None
    reason: str | None = None


def trial_window_closed(trial: TrialState, *, now: datetime) -> bool:
    """Whether the fourteen days have run out. The one place that comparison is made."""
    return trial.trial_started_at < now - timedelta(days=TRIAL_DAYS)


def trial_available(trial: TrialState, *, now: datetime) -> bool:
    """The free trial: three stations, each sat up to three times, within fourteen days.

    Stations are counted, not attempts: retrying a trial station never uses up another one. Set stations and
    completed stations are compared separately rather than summed, and the account age
    comparison is strict, so an account exactly fourteen days old still has its trial.
    """
    if trial_window_closed(trial, now=now):
        return False
    if trial.completed_on_this_station is not None:
        # A retry of a station already in the trial: only its own limit applies.
        return trial.completed_on_this_station < TRIAL_ATTEMPTS_PER_STATION
    if trial.set_station_count >= ALLOWED_TRIAL_STATIONS:
        return False
    return trial.completed_station_count < ALLOWED_TRIAL_STATIONS


def trial_stations_left(trial: TrialState, *, now: datetime) -> int:
    """How many new stations the free trial still covers: none once its window has closed.

    The two counters are weighed apart in `trial_available`, so the larger of them is what is used.
    """
    if trial_window_closed(trial, now=now):
        return 0
    used = max(trial.set_station_count, trial.completed_station_count)
    return max(0, ALLOWED_TRIAL_STATIONS - used)


def decide(
    grants: Sequence[Grant],
    *,
    now: datetime,
    trial: TrialState | None = None,
    exam_code: str | None = None,
) -> Decision:
    """The one question every attempt-creating path asks."""
    live = [grant for grant in grants if grant.live_at(now)]
    # A refunded purchase is not a lapsed subscription.
    lapsed = [grant for grant in grants if grant.revoked_at is None]
    if live:
        return Decision(allowed=True, source=live[0].source)

    if trial is not None:
        if trial_available(trial, now=now):
            return Decision(allowed=True, source="trial")
        # Somebody who once held a grant is a lapsed subscriber, not a used-up trial. Of a trial, the
        # screen needs to know whether its days ran out or only its stations, so they read differently.
        if lapsed:
            return Decision(allowed=False, reason="expired")
        return Decision(
            allowed=False,
            reason="trial_expired" if trial_window_closed(trial, now=now) else "trial_exhausted",
        )

    if lapsed:
        return Decision(allowed=False, reason="expired")
    return Decision(allowed=False, reason="no_entitlement")
