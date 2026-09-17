"""The errors the read models can answer with.

Both are `sittings`': a console for a circuit that is not this organisation's,
or a report for a sitting that is not, is the same refusal, with the same
code, as asking for that circuit or sitting directly. Re-exported rather than
redefined so the frontend keeps one code to switch on, and so the router
stays inside the rule that it imports only its own slice.
"""

from __future__ import annotations

from app.core.errors import InvalidInput
from app.features.sittings.errors import CircuitNotFound, SittingNotFound


class NotAnExamSitting(InvalidInput):
    """A cohort is only meaningful for an examination.

    The one error here this slice owns rather than borrows. Training is people
    practising, and ranking them against each other would turn practice into an
    assessment nobody agreed to sit. b2b answered 400; this is a 422, the
    platform's one code for a request that cannot mean anything.
    """

    code = "not_an_exam_sitting"
    default_message = "A cohort summary is only produced for an exam sitting"


__all__ = ["CircuitNotFound", "NotAnExamSitting", "SittingNotFound"]
