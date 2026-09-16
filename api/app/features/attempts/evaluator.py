"""Building the evaluator the scoring job uses.

The real implementation wraps `osce_assessment.evaluation.LLMEvaluator`, which
arrives when the engine becomes a versioned dependency rather than a vendored
subtree. Until then this raises rather than guessing, so a deployment that
tries to score without an engine says so plainly instead of writing an empty
result.
"""

from __future__ import annotations

from app.core.ports import EvaluationFailed, Evaluator


def build_evaluator() -> Evaluator:
    raise EvaluationFailed(
        "No evaluator configured. The osce_assessment engine is not yet wired as a "
        "dependency; see docs/OPEN-QUESTIONS.md."
    )
