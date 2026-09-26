"""Human judgement about a slot, beside the machine's.

Three kinds:

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


def normalize_rag(rating: str) -> str:
    key = (rating or "").strip().upper()
    if key not in RAG_VALUES:
        raise InvalidRag(f"{rating!r} is not one of {', '.join(RAG_VALUES)}.")
    return key


def normalize_status(status: str) -> str:
    key = (status or "").strip().lower()
    if key not in REVIEW_STATUSES:
        raise InvalidStatus(f"A review is {' or '.join(REVIEW_STATUSES)}, not {status!r}.")
    return key


def combine_rag(ratings: Sequence[str]) -> str | None:
    """One rating from several: the worst wins.

    When two reviewers disagree, the lower rating is the one that should
    prompt a conversation.
    """
    if not ratings:
        return None
    return min((normalize_rag(rating) for rating in ratings), key=lambda rating: _RAG_SEVERITY[rating])


def ensure_completable(*, scored: Collection[str], required: Collection[str], status: str) -> None:
    """A completed review has every reviewable domain scored, or it is refused."""
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
    """Optimistic concurrency for a GP-lead review: rejects a save based on a
    stale revision. A stored `None` is treated as revision zero."""
    if (stored or 0) != presented:
        raise ReviewConflict("Someone else has changed this review since you opened it. Reload and reapply.")
