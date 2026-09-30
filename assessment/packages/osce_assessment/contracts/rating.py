"""How one competency is rated, and what a result's fields mean.

A rubric rates every competency in its own units: a word on a scale, a number
in a range, or a yes/no. ``Rating`` holds those units and checks a value
against them. ``FieldRole`` is the closed list of meanings a result field can
have, so a reader (the debrief tutor, tutor memory, a dashboard) can find the
evidence or the missed items without knowing any field's name.

Nothing here knows which exam a rubric belongs to: an exam is data.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import model_validator

from ._base import Frozen

# The closed list of field meanings. A rubric author picks one per field; every
# reader downstream works from the role, never from the field's id.
FieldRole = Literal[
    "rating",  # the score itself
    "evidence",  # quotes and evidence points
    "explanation",  # why the score was given
    "strength",  # what went well
    "improvement",  # missed items and issues
    "action",  # suggested next steps
    "flag",  # critical concerns
    "summary",  # an overall narrative
    "selector",  # picks which domains apply (e.g. a station type)
    "other",  # anything else
]


class Rating(Frozen):
    """How a competency is rated: the native values its rating field may hold.

    ``rag`` and ``scale`` rate on the framework's ``scale`` (R/A/G, or any list
    of words an author chose). ``range`` rates on a number between ``minimum``
    and ``maximum``, whole when ``step`` is ``integer``. ``boolean`` rates
    competent or not.
    """

    kind: Literal["rag", "scale", "range", "boolean"] = "rag"
    minimum: float | None = None
    maximum: float | None = None
    step: Literal["number", "integer"] = "number"

    @model_validator(mode="after")
    def _check_bounds(self) -> "Rating":
        """A range needs both bounds, lowest first; nothing else uses them."""
        if self.kind != "range":
            return self
        if self.minimum is None or self.maximum is None:
            raise ValueError("a range rating needs a minimum and a maximum")
        if self.minimum >= self.maximum:
            raise ValueError(f"a range rating's minimum {self.minimum} must be below its maximum {self.maximum}")
        return self

    @property
    def is_enumerated(self) -> bool:
        """Whether a rating is one of a fixed list of values (the scale)."""
        return self.kind in ("rag", "scale")

    def accepts(self, value: Any, scale: tuple[str, ...]) -> bool:
        """Whether ``value`` is a rating this kind allows, given the framework's scale."""
        if self.is_enumerated:
            return isinstance(value, str) and value in scale
        if self.kind == "boolean":
            return isinstance(value, bool)
        # A range: a real number, never a bool (Python counts True as 1).
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        if self.step == "integer" and value != int(value):
            return False
        # The validator above guarantees both bounds exist for a range.
        assert self.minimum is not None and self.maximum is not None
        return self.minimum <= value <= self.maximum

    def describe(self, scale: tuple[str, ...]) -> str:
        """The allowed ratings in words, for an error message."""
        if self.is_enumerated:
            return f"one of {list(scale)}"
        if self.kind == "boolean":
            return "true or false"
        number_kind = "a whole number" if self.step == "integer" else "a number"
        return f"{number_kind} from {number_text(self.minimum)} to {number_text(self.maximum)}"


def number_text(value: float | int | None) -> str:
    """A number as a person writes it: ``7`` rather than ``7.0``, ``0.75`` as is."""
    if value is None:
        return ""
    return format(value, "g")
