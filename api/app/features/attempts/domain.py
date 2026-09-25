"""The attempt: one candidate running one scenario, however it was reached.

This is the shared core. A consumer practising alone, a trainee in an exam
slot, a debrief about an earlier attempt and a peer session all produce rows in
one table, because they are the same event with different reasons for being
allowed to happen.

Pure rules; the worker contract and the scoring job both depend on them.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum


class Status(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    INTERACTION_COMPLETE = "interaction_complete"
    EVALUATED = "evaluated"
    FAILED = "failed"


class Kind(StrEnum):
    PRACTICE = "practice"
    SET_STATION = "set_station"
    DEBRIEF = "debrief"
    SELF_PRACTICE = "self_practice"
    EXAM_SLOT = "exam_slot"
    PEER = "peer"


class InvalidTransition(Exception):
    pass


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


# Which optional foreign key each kind requires. The table enforces the same
# thing with a CHECK; this is what the service consults before writing.
def transition(current: Status, target: Status) -> Status:
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
