"""A candidate's outcome, and the workflow that gets it to them.

Revisions are append-only, the workflow is explicit, and the two outcomes are
checked against each other so a failed candidate cannot be recorded as hired.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from enum import StrEnum
from typing import Any

MAX_RATIONALE = 4000


class Assessment(StrEnum):
    """Whether a candidate met the standard on the exam itself."""

    PASS = "pass"  # noqa: S105 - an exam outcome, not a credential
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"
    WITHHELD = "withheld"


class Recruitment(StrEnum):
    """Whether an employer is taking this candidate on. Set only in hire mode."""

    HIRED = "hired"
    RESERVE = "reserve"
    NOT_HIRED = "not_hired"
    WITHDRAWN = "withdrawn"
    PENDING = "pending"


class Workflow(StrEnum):
    """Where a decision is: being written, signed off, or sent to the candidate."""

    DRAFT = "draft"
    SIGNED_OFF = "signed_off"
    RELEASED = "released"


class IncompatibleOutcomes(Exception):
    """An assessment and recruitment outcome that cannot go together."""


class NotSignable(Exception):
    """A decision that is missing what sign-off requires."""


class InvalidWorkflow(Exception):
    """A workflow step this decision cannot take from where it is."""


class EvidenceChanged(Exception):
    """The scores a decision was signed off against have since moved."""


class StaleDecision(Exception):
    """A save that named a revision older than the one now on record."""


class NotDecidable(Exception):
    """No outcome may be recorded for this candidate on this sitting (R-11)."""


class DecisionOutsideExam(NotDecidable):
    """A training sitting stops at marking: nobody records an outcome on practice."""


class CandidateDidNotSit(NotDecidable):
    """The candidate sat no station on this sitting, so there is no evidence to decide on."""


class RecruitmentOutsideExam(Exception):
    """A recruitment outcome on a training sitting, where nobody is being hired."""


# Oracle: `_OUTCOME_MATRIX`. A failed candidate cannot be hired or held in
# reserve, and an unresolved assessment cannot resolve recruitment either way.
_COMPATIBLE: Mapping[Assessment, frozenset[Recruitment]] = {
    Assessment.PASS: frozenset(Recruitment),
    Assessment.FAIL: frozenset({Recruitment.NOT_HIRED, Recruitment.WITHDRAWN}),
    Assessment.INCONCLUSIVE: frozenset({Recruitment.PENDING, Recruitment.WITHDRAWN}),
    Assessment.WITHHELD: frozenset({Recruitment.PENDING, Recruitment.WITHDRAWN}),
}

_ALLOWED_TRANSITIONS: Mapping[Workflow, frozenset[Workflow]] = {
    Workflow.DRAFT: frozenset({Workflow.SIGNED_OFF}),
    Workflow.SIGNED_OFF: frozenset({Workflow.RELEASED, Workflow.DRAFT}),
    Workflow.RELEASED: frozenset(),
}


def ensure_compatible(assessment: Assessment, recruitment: Recruitment | None) -> None:
    """A failed candidate cannot be hired, and an unresolved assessment cannot resolve recruitment."""
    if recruitment is None:
        return
    if recruitment not in _COMPATIBLE[assessment]:
        raise IncompatibleOutcomes(f"A {assessment} result cannot be recorded as {recruitment}.")


def ensure_signable(*, assessment: Assessment | None, rationale: str | None) -> None:
    """What a decision needs before anyone puts their name to it.

    A rationale is required so somebody can say why, months later, to a candidate or an appeal.
    """
    if assessment is None:
        raise NotSignable("An assessment outcome is required before sign-off.")
    text = (rationale or "").strip()
    if not text:
        raise NotSignable("A rationale is required before sign-off.")
    if len(text) > MAX_RATIONALE:
        raise NotSignable(f"A rationale is at most {MAX_RATIONALE} characters.")


def transition(current: Workflow, target: Workflow) -> Workflow:
    """Move the workflow forward (or back to draft), refusing any other step."""
    if target not in _ALLOWED_TRANSITIONS[current]:
        raise InvalidWorkflow(f"A result cannot go from {current} to {target}.")
    return target


def next_revision(stored: int | None) -> int:
    """The revision number a new save gets. `None` means nothing is recorded yet."""
    return (stored or 0) + 1


def ensure_current(*, stored: int | None, presented: int) -> None:
    """Optimistic concurrency for a decision drafted in two browsers.

    A save against a stale revision is refused rather than silently superseding
    a newer one. `0` asserts nothing has been recorded yet.
    """
    if (stored or 0) != presented:
        raise StaleDecision("Someone else has saved this decision since you opened it. Reload it first.")


def fingerprint(evidence: Mapping[str, Any]) -> str:
    """A stable hash of what a decision was made against.

    Sorted keys, so the same evidence hashes the same regardless of assembly order.
    """
    encoded = json.dumps(evidence, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode()).hexdigest()


def ensure_evidence_unchanged(*, signed: str, current: str) -> None:
    """A result signed off against one set of scores is not released after they move.

    Without this a station re-marked between sign-off and release would send a
    candidate an outcome nobody approved.
    """
    if signed != current:
        raise EvidenceChanged(
            "The evidence has changed since this was signed off. Review and sign off again."
        )


def ensure_recruitment_allowed(sitting_mode: str, recruitment: Recruitment | None) -> None:
    """Refuse a recruitment outcome outside exam mode.

    Hire is exam mode: a training sitting is practice, and a "hired" on it would be
    read by an employer as a decision nobody made.
    """
    if recruitment is not None and sitting_mode != "exam":
        raise RecruitmentOutsideExam


def ensure_decidable(*, sitting_mode: str, sat_a_station: bool) -> None:
    """Refuse a decision for a training sitting, or for somebody who sat nothing on it (R-11).

    A training sitting ends at Mark; a decision there would read as a verdict on
    practice. And an outcome for a candidate with no station sat is an outcome
    with no evidence behind it.
    """
    if sitting_mode != "exam":
        raise DecisionOutsideExam("Decisions are recorded for exam-mode sittings only.")
    if not sat_a_station:
        raise CandidateDidNotSit("This candidate did not sit any station on this sitting.")
