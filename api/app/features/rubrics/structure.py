"""The shape of an authored rubric, as plain data.

Its own module because both halves of this slice need it: `domain.py` parses a
stored structure into these, and `schema_builder.py` turns them into the JSON
Schema a marker fills. Neither may import the other.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

__all__ = ["CompetencySpec", "DomainSpec", "InvalidRubric", "RubricStructure", "SectionSpec"]


class InvalidRubric(ValueError):
    """A structure that cannot be marked against. The service maps this to 422."""


@dataclass(frozen=True)
class CompetencySpec:

    id: str
    label: str
    # What earns each point of the scale, keyed by scale value. Optional: a
    # rubric may name a competency without spelling out its anchors.
    descriptors: Mapping[str, str]


@dataclass(frozen=True)
class DomainSpec:

    id: str
    label: str
    # Whether this domain can be judged while the consultation is still
    # running. Whole-consultation judgements cannot, and say so here.
    live: bool
    competencies: tuple[CompetencySpec, ...]


@dataclass(frozen=True)
class SectionSpec:
    """A part of the result that is written rather than scored."""

    id: str
    label: str
    kind: str
    schema: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class RubricStructure:

    scale: tuple[str, ...]
    domains: tuple[DomainSpec, ...]
    sections: tuple[SectionSpec, ...]

    @property
    def competencies(self) -> tuple[CompetencySpec, ...]:
        return tuple(competency for domain in self.domains for competency in domain.competencies)
