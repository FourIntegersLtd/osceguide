"""Human judgement about a slot, beside the machine's.

Three kinds, which b2b keeps in one wide table discriminated by a column and
with no foreign keys at all:

- a **slot review**: a rubric filled in by staff, or by a peer observing;
- a **GP-lead review**: a revisioned second opinion on a slot;
- a **circuit review**: the aggregate a supervisor finalises for a whole circuit.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence

RAG_VALUES = ("R", "A", "G")
REVIEW_STATUSES = ("draft", "completed")

# Worst first, so a tie between reviewers resolves downward.
_RAG_SEVERITY = {"R": 0, "A": 1, "G": 2}


class InvalidRag(ValueError):
    pass


class InvalidStatus(ValueError):
    pass


class ReviewIncomplete(Exception):
    pass


class NothingToReview(Exception):
    pass


class ReviewConflict(Exception):
    pass


def normalize_rag(value: str) -> str:
    key = (value or "").strip().upper()
    if key not in RAG_VALUES:
        raise InvalidRag(f"{value!r} is not one of {', '.join(RAG_VALUES)}.")
    return key


def normalize_status(value: str) -> str:
    key = (value or "").strip().lower()
    if key not in REVIEW_STATUSES:
        raise InvalidStatus(f"A review is {' or '.join(REVIEW_STATUSES)}, not {value!r}.")
    return key


def combine_rag(values: Sequence[str]) -> str | None:
    """One rating from several.

    The worst wins. Ported from b2b's tie-break, and worth keeping deliberately:
    when two reviewers disagree about a candidate, the lower rating is the one
    that should prompt a conversation.
    """
    if not values:
        return None
    return min((normalize_rag(v) for v in values), key=lambda r: _RAG_SEVERITY[r])


def ensure_completable(*, scored: Collection[str], required: Collection[str], status: str) -> None:
    """A completed review has every reviewable domain scored.

    A half-marked review shown to a candidate is worse than one still openly in
    progress, so this is refused rather than warned about.
    """
    if normalize_status(status) != "completed":
        return
    if not required:
        raise NothingToReview(
            "This station has no reviewable feedback domains yet, so there is nothing to complete."
        )
    missing = sorted(set(required) - set(scored))
    if missing:
        raise ReviewIncomplete(
            "Score every domain before completing the review; still missing: " + ", ".join(missing)
        )


def next_revision(stored: int | None) -> int:
    return (stored or 0) + 1


def ensure_current(*, stored: int | None, presented: int) -> None:
    """Optimistic concurrency for a GP-lead review.

    Two reviewers can have the same screen open. Without this the second save
    silently overwrites the first, and nobody finds out. A stored `None` is a
    row predating the field, which b2b treats as revision zero and which must
    stay writable.
    """
    if (stored or 0) != presented:
        raise ReviewConflict("Someone else has changed this review since you opened it. Reload and reapply.")
