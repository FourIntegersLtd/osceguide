"""Scoring a transcript against a framework, under a policy."""

from .evaluator import EvaluationError, LLMEvaluator, ProviderError
from .live_coverage import (
    CoverageItem,
    CoverageSnapshot,
    CoverageState,
    LiveCoverageDetector,
    LiveCoverageError,
    live_competency_ids,
    recent_window,
)
from .rendering import render_transcript_for_marking

__all__ = [
    "CoverageItem",
    "CoverageSnapshot",
    "CoverageState",
    "EvaluationError",
    "LLMEvaluator",
    "LiveCoverageDetector",
    "LiveCoverageError",
    "ProviderError",
    "live_competency_ids",
    "recent_window",
    "render_transcript_for_marking",
]
