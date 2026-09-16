"""Human feedback rules, ported from b2b.

Sources: `sessions/slot_review.py:25-26` (RAG and status), `:321-339` (what
"completed" requires), `feedback/_shared.py:25-38` (revision handling).
"""

from __future__ import annotations

import pytest

from app.features.reviews import domain

# --------------------------------------------------------------------------
# RAG
# --------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["R", "A", "G"])
def test_the_three_rag_values(value: str) -> None:
    assert domain.normalize_rag(value) == value


@pytest.mark.parametrize("value", ["r", " g ", "a"])
def test_rag_is_normalised(value: str) -> None:
    assert domain.normalize_rag(value) in {"R", "A", "G"}


def test_anything_else_is_refused() -> None:
    with pytest.raises(domain.InvalidRag):
        domain.normalize_rag("X")


def test_the_worst_rating_wins_a_tie() -> None:
    """Oracle: b2b's majority with a worst-case tie-break. A candidate is not
    given the benefit of the doubt when two reviewers disagree."""
    assert domain.combine_rag(["G", "R"]) == "R"
    assert domain.combine_rag(["G", "A"]) == "A"
    assert domain.combine_rag(["G", "G"]) == "G"


def test_combining_nothing_gives_nothing() -> None:
    assert domain.combine_rag([]) is None


# --------------------------------------------------------------------------
# Completing a review
# --------------------------------------------------------------------------


def test_a_draft_may_leave_domains_unscored() -> None:
    domain.ensure_completable(
        scored={"communication"}, required={"communication", "management"}, status="draft"
    )


def test_completing_requires_every_domain() -> None:
    """Oracle: slot_review.py:321. A half-marked review shown to a candidate is
    worse than one still in progress."""
    with pytest.raises(domain.ReviewIncomplete) as exc:
        domain.ensure_completable(
            scored={"communication"}, required={"communication", "management"}, status="completed"
        )
    assert "management" in str(exc.value)


def test_completing_with_everything_scored_is_allowed() -> None:
    domain.ensure_completable(
        scored={"communication", "management"},
        required={"communication", "management"},
        status="completed",
    )


def test_completing_with_nothing_reviewable_is_refused() -> None:
    """Oracle: "No reviewable AI domains are available for this station yet"."""
    with pytest.raises(domain.NothingToReview):
        domain.ensure_completable(scored=set(), required=set(), status="completed")


@pytest.mark.parametrize("status", ["draft", "completed"])
def test_valid_statuses(status: str) -> None:
    assert domain.normalize_status(status) == status


def test_an_unknown_status_is_refused() -> None:
    with pytest.raises(domain.InvalidStatus):
        domain.normalize_status("published")


# --------------------------------------------------------------------------
# Optimistic concurrency on a GP-lead review
# --------------------------------------------------------------------------


def test_the_first_revision_is_one() -> None:
    assert domain.next_revision(None) == 1


def test_a_revision_advances() -> None:
    assert domain.next_revision(3) == 4


def test_writing_against_the_current_revision_is_allowed() -> None:
    domain.ensure_current(stored=3, presented=3)


def test_writing_against_a_stale_revision_is_refused() -> None:
    """Two reviewers with the screen open; the second must not silently
    overwrite the first."""
    with pytest.raises(domain.ReviewConflict):
        domain.ensure_current(stored=4, presented=3)


def test_a_legacy_row_without_a_revision_is_treated_as_zero() -> None:
    """Oracle: `_shared.gp_lead_revision_from_context` — rows predating the
    field exist and must stay writable."""
    domain.ensure_current(stored=None, presented=0)
