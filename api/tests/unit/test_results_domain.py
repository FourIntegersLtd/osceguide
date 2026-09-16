"""Candidate outcomes, ported from b2b's `sql/017` and `results/service.py`.

This is the one piece of legacy design better than anything we would write from
scratch: append-only revisions, an explicit workflow, and a compatibility matrix
between the two outcomes. It is ported, not reinvented.
"""

from __future__ import annotations

import pytest

from app.features.results import domain
from app.features.results.domain import Assessment, Recruitment, Workflow

# --------------------------------------------------------------------------
# The outcome matrix (oracle: results/service.py:16-21)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "recruitment",
    [
        Recruitment.HIRED,
        Recruitment.RESERVE,
        Recruitment.NOT_HIRED,
        Recruitment.WITHDRAWN,
        Recruitment.PENDING,
    ],
)
def test_a_pass_is_compatible_with_any_recruitment_outcome(recruitment: Recruitment) -> None:
    domain.ensure_compatible(Assessment.PASS, recruitment)


@pytest.mark.parametrize("recruitment", [Recruitment.NOT_HIRED, Recruitment.WITHDRAWN])
def test_a_fail_allows_only_not_hired_or_withdrawn(recruitment: Recruitment) -> None:
    domain.ensure_compatible(Assessment.FAIL, recruitment)


@pytest.mark.parametrize("recruitment", [Recruitment.HIRED, Recruitment.RESERVE, Recruitment.PENDING])
def test_a_fail_cannot_be_hired(recruitment: Recruitment) -> None:
    """The check that stops a failed candidate being recorded as appointed."""
    with pytest.raises(domain.IncompatibleOutcomes):
        domain.ensure_compatible(Assessment.FAIL, recruitment)


@pytest.mark.parametrize("assessment", [Assessment.INCONCLUSIVE, Assessment.WITHHELD])
def test_an_unresolved_assessment_leaves_recruitment_pending(assessment: Assessment) -> None:
    domain.ensure_compatible(assessment, Recruitment.PENDING)
    with pytest.raises(domain.IncompatibleOutcomes):
        domain.ensure_compatible(assessment, Recruitment.HIRED)


# --------------------------------------------------------------------------
# Sign-off
# --------------------------------------------------------------------------


def test_signing_off_needs_an_assessment_outcome() -> None:
    with pytest.raises(domain.NotSignable):
        domain.ensure_signable(assessment=None, rationale="Because.")


def test_signing_off_needs_a_rationale() -> None:
    """Somebody has to be able to say why, months later."""
    with pytest.raises(domain.NotSignable):
        domain.ensure_signable(assessment=Assessment.PASS, rationale="  ")


def test_a_rationale_has_a_limit() -> None:
    """Oracle: 4000 characters."""
    with pytest.raises(domain.NotSignable):
        domain.ensure_signable(assessment=Assessment.PASS, rationale="x" * 4001)


def test_a_complete_decision_is_signable() -> None:
    domain.ensure_signable(assessment=Assessment.PASS, rationale="Met the standard.")


# --------------------------------------------------------------------------
# Workflow
# --------------------------------------------------------------------------


def test_a_draft_may_be_signed_off() -> None:
    assert domain.transition(Workflow.DRAFT, Workflow.SIGNED_OFF) is Workflow.SIGNED_OFF


def test_a_signed_off_decision_may_be_released() -> None:
    assert domain.transition(Workflow.SIGNED_OFF, Workflow.RELEASED) is Workflow.RELEASED


def test_a_draft_cannot_be_released_directly() -> None:
    """Release is what a candidate sees, so it goes through sign-off."""
    with pytest.raises(domain.InvalidWorkflow):
        domain.transition(Workflow.DRAFT, Workflow.RELEASED)


def test_a_released_decision_is_final() -> None:
    with pytest.raises(domain.InvalidWorkflow):
        domain.transition(Workflow.RELEASED, Workflow.DRAFT)


def test_revisions_are_numbered_from_one_and_chain() -> None:
    assert domain.next_revision(None) == 1
    assert domain.next_revision(2) == 3


# --------------------------------------------------------------------------
# Evidence fingerprint
# --------------------------------------------------------------------------


def test_the_fingerprint_is_stable_for_the_same_evidence() -> None:
    evidence = {"slots": ["a", "b"], "scores": {"x": 1}}
    assert domain.fingerprint(evidence) == domain.fingerprint(dict(evidence))


def test_the_fingerprint_ignores_key_order() -> None:
    assert domain.fingerprint({"a": 1, "b": 2}) == domain.fingerprint({"b": 2, "a": 1})


def test_different_evidence_fingerprints_differently() -> None:
    assert domain.fingerprint({"a": 1}) != domain.fingerprint({"a": 2})


def test_releasing_needs_the_evidence_to_be_unchanged() -> None:
    """Oracle: `b2b_release_candidate_result` compares the fingerprint.

    A result signed off against one set of station scores must not be released
    after those scores have moved.
    """
    domain.ensure_evidence_unchanged(signed="abc", current="abc")
    with pytest.raises(domain.EvidenceChanged):
        domain.ensure_evidence_unchanged(signed="abc", current="def")
