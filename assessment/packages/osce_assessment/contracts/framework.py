"""What a competency framework is.

A framework owns the *shape* of a result: which domains and competencies exist,
and what scores may be given. An ``EvaluationPolicy`` owns the *scoring*: which
model runs, which prompt, which thresholds, which version.

Shape is expressed as data, not as a Python class, so a framework can equally
describe a platform exam or one an organisation authored. Every framework now
arrives as a row somebody wrote through an API; nothing here knows or cares
where it was loaded from.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import Field, model_validator

from ._base import Frozen

# The platform's existing marking convention: red, amber, green.
RAG_SCALE: tuple[str, ...] = ("R", "A", "G")


class UnknownCompetencyError(LookupError):
    """A score was given for a competency the framework does not define."""


class InvalidScoreError(ValueError):
    """A score was given that is not on the framework's scale."""


class CompetencyDomain(Frozen):
    """A grouping of competencies, e.g. the global skills of a consultation."""

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    # Whether this domain is worth watching while the consultation is still
    # running. Was a tuple of two domain ids in `live_coverage`, which only
    # ever matched the framework the platform happened to ship.
    live: bool = False


class Competency(Frozen):
    """One thing a candidate is marked on."""

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    domain_id: str = Field(min_length=1)
    # What earns each point on the scale, keyed by scale value. These were the
    # `description` strings buried in the hand-written JSON schemas, which is
    # why nobody could edit a rubric without editing the package.
    descriptors: dict[str, str] = Field(default_factory=dict)


class CompetencyFramework(Frozen):
    """The domains, competencies and scale that define a result's shape."""

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    version: str = "1"
    domains: tuple[CompetencyDomain, ...] = ()
    competencies: tuple[Competency, ...] = ()
    scale: tuple[str, ...] = RAG_SCALE
    # Optional structural description of the result payload, for frameworks
    # whose shape is richer than a flat set of scored competencies.
    result_schema: dict[str, Any] | None = None
    # The marking instructions. Was one of three .txt files chosen by a dict
    # keyed on framework id; now it travels with the framework that needs it.
    system_prompt: str | None = None

    @model_validator(mode="after")
    def _check_internal_consistency(self) -> "CompetencyFramework":
        if not self.scale:
            raise ValueError(f"framework {self.id} has an empty scale")
        domain_ids = [domain.id for domain in self.domains]
        if len(set(domain_ids)) != len(domain_ids):
            raise ValueError(f"framework {self.id} has duplicate domain ids")
        competency_ids = [competency.id for competency in self.competencies]
        if len(set(competency_ids)) != len(competency_ids):
            raise ValueError(f"framework {self.id} has duplicate competency ids")
        orphans = sorted(
            {c.id for c in self.competencies if c.domain_id not in set(domain_ids)}
        )
        if orphans:
            raise ValueError(
                f"framework {self.id} has competencies in undeclared domains: {orphans}"
            )
        scale = set(self.scale)
        off_scale = sorted(
            {
                f"{c.id}.{key}"
                for c in self.competencies
                for key in c.descriptors
                if key not in scale
            }
        )
        if off_scale:
            raise ValueError(
                f"framework {self.id} describes scores outside its scale: {off_scale}"
            )
        return self

    @property
    def domain_ids(self) -> tuple[str, ...]:
        return tuple(domain.id for domain in self.domains)

    @property
    def live_domain_ids(self) -> tuple[str, ...]:
        """The domains worth reporting on mid-consultation."""
        return tuple(domain.id for domain in self.domains if domain.live)

    @property
    def competency_ids(self) -> tuple[str, ...]:
        return tuple(competency.id for competency in self.competencies)

    def competencies_in(self, domain_id: str) -> tuple[Competency, ...]:
        return tuple(c for c in self.competencies if c.domain_id == domain_id)

    def validate_scores(self, scores: Mapping[str, str]) -> None:
        """Check a competency-to-score mapping against this framework.

        Raises ``UnknownCompetencyError`` or ``InvalidScoreError``. A framework
        with no declared competencies accepts anything, which is what lets a
        schema-only framework pass through untouched.
        """
        if not self.competencies:
            return
        known = set(self.competency_ids)
        unknown = sorted(set(scores) - known)
        if unknown:
            raise UnknownCompetencyError(
                f"framework {self.id} does not define {unknown}"
            )
        off_scale = sorted(
            {value for value in scores.values() if value not in self.scale}
        )
        if off_scale:
            raise InvalidScoreError(
                f"framework {self.id} scores must be one of {list(self.scale)}; "
                f"got {off_scale}"
            )
