"""A rating in words, from the rating's own kind and bounds.

Written for the page ("7/10", "Amber", "competent") or for speech ("7 out of
10", "competent", "strong"). Every reader of a marked result words ratings
here, so no reader needs to know which exam used which units.
"""

from __future__ import annotations

from typing import Any

from ..contracts import Rating
from ..contracts.rating import number_text

# The written names of the three R/A/G values, which a ``rag`` rating stores
# as single letters.
RAG_WRITTEN = {"G": "Green", "A": "Amber", "R": "Red"}
# The same values said to a learner: how the domain went, not a colour code.
RAG_SPOKEN = {"G": "strong", "A": "competent", "R": "needs work"}


def rating_text(rating: Rating, value: Any, *, spoken: bool = False) -> str:
    """One rating in words, or an empty string when there is nothing to say.

    ``spoken`` writes numbers the way they are said, for a voice tutor.
    """
    if value is None or value == "":
        return ""
    if rating.kind == "boolean" and isinstance(value, bool):
        return "competent" if value else "not yet competent"
    if rating.kind == "rag":
        # Stored as a letter; older summaries sometimes spelled the colour out.
        cleaned = str(value).strip().upper()
        letter = cleaned[:1] if cleaned in ("G", "A", "R", "GREEN", "AMBER", "RED") else cleaned
        words = RAG_SPOKEN if spoken else RAG_WRITTEN
        return words.get(letter, str(value))
    if rating.kind == "range" and isinstance(value, (int, float)) and not isinstance(value, bool):
        joiner = " out of " if spoken else "/"
        return f"{number_text(value)}{joiner}{number_text(rating.maximum)}"
    # A ``scale`` rating is already a word the author chose.
    return str(value)
