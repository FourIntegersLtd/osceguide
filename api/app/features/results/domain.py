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
    PASS = "pass"  # noqa: S105 - an exam outcome, not a credential
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"
    WITHHELD = "withheld"


class Recruitment(StrEnum):
    HIRED = "hired"
    RESERVE = "reserve"
    NOT_HIRED = "not_hired"
    WITHDRAWN = "withdrawn"
    PENDING = "pending"


class Workflow(StrEnum):
    DRAFT = "draft"
    SIGNED_OFF = "signed_off"
    RELEASED = "released"


class IncompatibleOutcomes(Exception):
    pass


class NotSignable(Exception):
    pass


class InvalidWorkflow(Exception):
    pass


class EvidenceChanged(Exception):
    pass


class StaleDecision(Exception):
    pass


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
    if target not in _ALLOWED_TRANSITIONS[current]:
        raise InvalidWorkflow(f"A result cannot go from {current} to {target}.")
    return target


def next_revision(stored: int | None) -> int:
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
