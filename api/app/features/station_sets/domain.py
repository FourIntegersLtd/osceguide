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
    pass


class SetLocked(Exception):
    pass


class NothingToDebrief(Exception):
    pass


@dataclass(frozen=True)
class EntryState:

    attempts: int = 0
    debrief_attempts: int = 0


def ensure_attemptable(entry: EntryState, *, limit: int, locked: bool) -> None:
    if locked:
        raise SetLocked("This set is locked because your access has lapsed.")
    # Zero means unlimited, which is what an org-granted set uses.
    if limit and entry.attempts >= limit:
        raise AttemptLimitReached(f"This station has been attempted {limit} times.")


def ensure_debriefable(entry: EntryState, *, limit: int) -> None:
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
