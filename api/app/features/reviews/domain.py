"""Human judgement about a slot, beside the machine's.

Three kinds:

- a **slot review**: a rubric filled in by staff, or by a peer observing;
- a **GP-lead review**: a revisioned second opinion on a slot;
- a **circuit review**: the aggregate a supervisor finalises for a whole circuit.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping

REVIEW_STATUSES = ("draft", "completed")

# A GP lead's own overall verdict on a slot: a traffic light, whatever the
# rubric rates competencies in. It is the lead's judgement, not a rubric
# rating, and is stored in a one-letter column.
GP_LEAD_VERDICTS = ("G", "A", "R")


class InvalidVerdict(ValueError):
    """Raised when a GP lead's overall verdict is not G, A or R."""


class InvalidStatus(ValueError):
    """Raised when a review status is not draft or completed."""


class ReviewIncomplete(Exception):
    """Raised when a review is marked completed without scoring every required domain."""


class NothingToReview(Exception):
    """Raised when a station has no reviewable feedback domains at all."""


class ReviewConflict(Exception):
    """Raised when a GP-lead review is saved against a stale revision."""


def normalize_verdict(verdict: str) -> str:
    """A GP lead's overall verdict as G, A or R, whatever case or spacing it arrived in."""
    key = (verdict or "").strip().upper()
    if key not in GP_LEAD_VERDICTS:
        raise InvalidVerdict(f"{verdict!r} is not one of {', '.join(GP_LEAD_VERDICTS)}.")
    return key


def normalize_status(status: str) -> str:
    """A review status as draft or completed, whatever case it arrived in."""
    key = (status or "").strip().lower()
    if key not in REVIEW_STATUSES:
        raise InvalidStatus(f"A review is {' or '.join(REVIEW_STATUSES)}, not {status!r}.")
    return key


def ensure_completable(*, scored: Collection[str], required: Mapping[str, str], status: str) -> None:
    """A completed review has every reviewable domain scored, or it is refused.

    `required` maps each domain id to its rubric title, in the rubric's order, so the
    refusal names what the reviewer sees on the form rather than an id (B55).
    """
    if normalize_status(status) != "completed":
        return
    if not required:
        raise NothingToReview(
            "This station has no reviewable feedback domains yet, so there is nothing to complete."
        )
    missing = [title for domain_id, title in required.items() if domain_id not in scored]
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
