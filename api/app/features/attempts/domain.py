"""The attempt: one candidate running one scenario, however it was reached.

This is the shared core. A consumer practising alone, a trainee in an exam
slot, a debrief about an earlier attempt and a peer session all produce rows in
one table, because they are the same event with different reasons for being
allowed to happen.

Pure rules; the worker contract and the scoring job both depend on them.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum


class Status(StrEnum):
    """Where one attempt is in its life, from creation to a stored score."""

    CREATED = "created"
    RUNNING = "running"
    INTERACTION_COMPLETE = "interaction_complete"
    EVALUATED = "evaluated"
    FAILED = "failed"


# Why a finished attempt carries a `failed_reason`. The first leaves the transcript markable (the
# scorer gave up; staff can retry); the second fails the attempt, which has nothing to be marked against.
SCORING_FAILED = "scoring_failed"
NO_MARKING_RUBRIC = "no_marking_rubric"


def marking_failed(status: str, failed_reason: str | None) -> bool:
    """The scorer gave up on a finished attempt whose transcript is still held (R-5)."""
    return status == Status.INTERACTION_COMPLETE and failed_reason == SCORING_FAILED


class Kind(StrEnum):
    """Why this attempt exists, which decides the one reference it may carry (see the glossary)."""

    PRACTICE = "practice"
    SET_STATION = "set_station"
    DEBRIEF = "debrief"
    SELF_PRACTICE = "self_practice"
    EXAM_SLOT = "exam_slot"
    PEER = "peer"


class InvalidTransition(Exception):
    """Raised when the service tries to move an attempt to a status it cannot reach from here."""


class UnrenderableDefinition(Exception):
    """A definition with no instructions. The worker refuses these, so refusing
    them here turns a job that dies on connect into an error at creation."""


_ALLOWED: Mapping[Status, frozenset[Status]] = {
    Status.CREATED: frozenset({Status.RUNNING, Status.FAILED}),
    Status.RUNNING: frozenset({Status.INTERACTION_COMPLETE, Status.FAILED}),
    Status.INTERACTION_COMPLETE: frozenset({Status.EVALUATED, Status.FAILED}),
    Status.EVALUATED: frozenset(),
    Status.FAILED: frozenset(),
}


def transition(current: Status, target: Status) -> Status:
    """Move an attempt from `current` to `target`, or refuse a move the lifecycle forbids."""
    if target not in _ALLOWED[current]:
        raise InvalidTransition(f"An attempt cannot go from {current} to {target}.")
    return target


# What a candidate may read back about their own attempt.
#
# The management plan and the patient's ideas, concerns and expectations are
# the model answer: showing them before the consultation is showing the answer,
# so the review read is refused until the interaction is over. `failed` is here
# because abandoning writes it — somebody who walked out still sat the station
# and may read what they missed.
REVIEWABLE = frozenset({Status.INTERACTION_COMPLETE, Status.EVALUATED, Status.FAILED})


def is_reviewable(status: Status) -> bool:
    return status in REVIEWABLE


# Walking away is only possible while there is something to walk away from.
# Once the interaction is complete the transcript exists and is being marked:
# that attempt is finished, and "abandoning" it would throw away a recording
# the candidate is entitled to the feedback from.
ABANDONABLE = frozenset({Status.CREATED, Status.RUNNING})


def ensure_abandonable(current: Status) -> None:
    """Refuse to abandon an attempt whose interaction is already over."""
    if current not in ABANDONABLE:
        raise InvalidTransition(f"An attempt that is {current} cannot be abandoned.")


def should_freeze(*, render_degraded: bool, already_frozen: bool) -> bool:
    """Whether this render should become the attempt's frozen definition.

    Frozen once, on the first *successful* render. Both legacy backends freeze
    unconditionally, so an unresolved station pins a generic patient prompt to
    the attempt permanently, and a debrief whose context was incomplete pins a
    prompt carrying no transcript ids — the live insights panel then stays
    empty for the whole session and every replay of it.
    """
    return not already_frozen and not render_degraded


def should_store_chunk(message_id: str, seen: frozenset[str] | set[str]) -> bool:
    """Chunks repeat. The worker posts them best-effort and never reads the
    response, so the same turn can arrive more than once."""
    return message_id not in seen


def should_accept_transcript(*, already_complete: bool) -> bool:
    return not already_complete


def should_score(*, scored_versions: frozenset[str] | set[str], policy_version: str) -> bool:
    """Scoring is keyed by policy version.

    Re-running the same policy stores nothing new; scoring under a different
    one — a new org rubric, a changed model — is a new result beside the old,
    never a replacement, so a candidate's history stays readable.
    """
    return policy_version not in scored_versions


@dataclass(frozen=True)
class TrialAttempt:
    """One attempt as the free-trial rule sees it."""

    attempt_id: uuid.UUID
    kind: str
    status: str
    # None for an attempt that ran without a station.
    station_version_id: uuid.UUID | None


@dataclass(frozen=True)
class TrialCounts:
    """What the free-trial rule needs from this person's attempts on one exam."""

    # Distinct stations sat as part of a practice set.
    set_stations: int
    # Distinct stations finished at least once.
    completed_stations: int
    # Whether the station being started already has an attempt, so starting it is a retry.
    started_this_station: bool
    # How many times the station being started has been finished.
    completed_on_this_station: int


# The statuses that mean the candidate got to the end of the station.
_FINISHED = frozenset({Status.INTERACTION_COMPLETE, Status.EVALUATED})


def count_trial_use(
    trial_attempts: Sequence[TrialAttempt],
    *,
    station_by_version: Mapping[uuid.UUID, uuid.UUID],
    starting_station_id: uuid.UUID | None,
) -> TrialCounts:
    """The free-trial counters, counted by station rather than by attempt.

    Two attempts at two versions of one station are the same station, which is
    why `station_by_version` is needed. An attempt with no station counts as a
    station of its own, so it uses up one of the trial's stations.
    `starting_station_id` is the station about to be started, or None when the
    question is only whether any trial is left.
    """
    set_stations: set[uuid.UUID] = set()
    completed_stations: set[uuid.UUID] = set()
    attempts_on_this_station = 0
    completed_on_this_station = 0
    for trial_attempt in trial_attempts:
        station_key = trial_attempt.attempt_id
        if trial_attempt.station_version_id is not None:
            station_key = station_by_version.get(trial_attempt.station_version_id, trial_attempt.attempt_id)
        finished = trial_attempt.status in _FINISHED
        if trial_attempt.kind == Kind.SET_STATION:
            set_stations.add(station_key)
        if finished:
            completed_stations.add(station_key)
        if starting_station_id is not None and station_key == starting_station_id:
            attempts_on_this_station += 1
            completed_on_this_station += int(finished)
    return TrialCounts(
        set_stations=len(set_stations),
        completed_stations=len(completed_stations),
        started_this_station=attempts_on_this_station > 0,
        completed_on_this_station=completed_on_this_station,
    )
