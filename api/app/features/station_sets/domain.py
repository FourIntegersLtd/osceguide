"""A reusable practice set — what b2c calls a mock.

Deliberately not a circuit. A set is a personal collection a learner returns to:
its entries carry attempt counters, and the whole thing locks when access lapses
rather than being deleted, so the work reappears on renewal. A circuit slot is
one-shot and scheduled by somebody else.

Collapsing the two would give a slot an attempt counter and a lock flag, which
is the b2b shape in reverse.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


class AttemptLimitReached(Exception):
    """Raised when a candidate has already used every attempt an exam allows at a station."""


class SetLocked(Exception):
    """Raised when a learner tries to attempt a station in a set whose access has lapsed."""


class NothingToDebrief(Exception):
    """Raised when a debrief is asked for on a station nobody has attempted yet."""


@dataclass(frozen=True)
class EntryState:
    """The parts of a set entry the attempt and debrief rules look at."""

    attempts: int = 0
    debrief_attempts: int = 0


def ensure_attemptable(entry: EntryState, *, limit: int, locked: bool) -> None:
    """Refuse to start an attempt if the set is locked or this station's limit is used up."""
    if locked:
        raise SetLocked("This set is locked because your access has lapsed.")
    # Zero means unlimited, which is what an org-granted set uses.
    if limit and entry.attempts >= limit:
        raise AttemptLimitReached(f"This station has been attempted {limit} times.")


def ensure_debriefable(entry: EntryState, *, limit: int) -> None:
    """Refuse a debrief if the station has never been attempted or its debrief limit is used up."""
    if entry.attempts < 1:
        raise NothingToDebrief("Run the station before asking for a debrief about it.")
    if limit and entry.debrief_attempts >= limit:
        raise AttemptLimitReached(f"This station has been debriefed {limit} times.")


def set_complete(entries: Sequence[EntryState]) -> bool:
    """Every entry attempted at least once.

    An empty set is not complete: otherwise one created and never populated
    reports itself finished the moment it exists.
    """
    return bool(entries) and all(entry.attempts > 0 for entry in entries)


def progress(entries: Sequence[EntryState]) -> tuple[int, int]:
    return sum(1 for entry in entries if entry.attempts > 0), len(entries)
