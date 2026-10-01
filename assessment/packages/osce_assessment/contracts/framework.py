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
from .rating import FieldRole, Rating

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
    # Whether a result may leave this domain null: a rubric that marks one
    # station type per interview leaves the other domains legitimately absent.
    nullable: bool = False


class Competency(Frozen):
    """One thing a candidate is marked on."""

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    domain_id: str = Field(min_length=1)
    # What earns each point on the scale, keyed by scale value. These were the
    # `description` strings buried in the hand-written JSON schemas, which is
    # why nobody could edit a rubric without editing the package.
    descriptors: dict[str, str] = Field(default_factory=dict)

    @property
    def local_id(self) -> str:
        """The id the result nests this competency under, inside its domain.

        platform-api qualifies ids as ``domain.competency`` so one name can
        appear in several domains; the result still uses the bare name.
        """
        prefix = f"{self.domain_id}."
        return self.id[len(prefix):] if self.id.startswith(prefix) else self.id


class CompetencyFramework(Frozen):
    """The domains, competencies and scale that define a result's shape."""

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    version: str = "1"
    domains: tuple[CompetencyDomain, ...] = ()
    competencies: tuple[Competency, ...] = ()
    scale: tuple[str, ...] = RAG_SCALE
    # The native kind of rating, and the field inside each competency's result
    # object that holds it (``score``, ``competent``). With no ``rating_field``
    # the framework cannot read ratings out of a result and checks none.
    rating: Rating = Field(default_factory=Rating)
    rating_field: str | None = None
    # What each result field means (field id -> role), for competency and
    # domain fields alike. Readers such as the debrief tutor walk a result by
    # role, never by field name. Absent (a v1 payload), every field but the
    # rating field reads as ``other``.
    field_roles: dict[str, FieldRole] = Field(default_factory=dict)
    # Optional structural description of the result payload, for frameworks
    # whose shape is richer than a flat set of scored competencies.
    result_schema: dict[str, Any] | None = None
    # The marking instructions. Was one of three .txt files chosen by a dict
    # keyed on framework id; now it travels with the framework that needs it.
    system_prompt: str | None = None

    @model_validator(mode="after")
    def _check_internal_consistency(self) -> "CompetencyFramework":
        """Refuse a framework whose parts contradict each other."""
        if self.rating.is_enumerated and not self.scale:
            raise ValueError(f"framework {self.id} has an empty scale")
        domain_ids = [domain.id for domain in self.domains]
        if len(set(domain_ids)) != len(domain_ids):
            raise ValueError(f"framework {self.id} has duplicate domain ids")
        competency_ids = [competency.id for competency in self.competencies]
        if len(set(competency_ids)) != len(competency_ids):
            raise ValueError(f"framework {self.id} has duplicate competency ids")
        orphans = sorted(
            {competency.id for competency in self.competencies if competency.domain_id not in set(domain_ids)}
        )
        if orphans:
            raise ValueError(
                f"framework {self.id} has competencies in undeclared domains: {orphans}"
            )
        scale = set(self.scale)
        off_scale = sorted(
            {
                f"{competency.id}.{key}"
                for competency in self.competencies
                for key in competency.descriptors
                if self.rating.is_enumerated and key not in scale
            }
        )
        if off_scale:
            raise ValueError(
                f"framework {self.id} describes scores outside its scale: {off_scale}"
            )
        if self.rating_field and self.field_roles.get(self.rating_field, "rating") != "rating":
            raise ValueError(
                f"framework {self.id} gives its rating field {self.rating_field!r} the role "
                f"{self.field_roles[self.rating_field]!r}"
            )
        return self

    @property
    def domain_ids(self) -> tuple[str, ...]:
        """Every domain id, in the framework's order."""
        return tuple(domain.id for domain in self.domains)

    @property
    def live_domain_ids(self) -> tuple[str, ...]:
        """The domains worth reporting on mid-consultation."""
        return tuple(domain.id for domain in self.domains if domain.live)

    @property
    def competency_ids(self) -> tuple[str, ...]:
        """Every competency id, in the framework's order."""
        return tuple(competency.id for competency in self.competencies)

    def competencies_in(self, domain_id: str) -> tuple[Competency, ...]:
        """The competencies marked under one domain."""
        return tuple(competency for competency in self.competencies if competency.domain_id == domain_id)

    def scores_in(self, result: Mapping[str, Any]) -> dict[str, Any]:
        """Every competency's rating in a result, keyed by competency id.

        A competency id may be qualified as ``domain.competency`` (a rubric may
        use one competency name in several domains); the result nests it
        under its domain by the local name either way. A nullable domain the
        result left null contributes nothing, and neither does a competency
        whose rating field is absent: the schema decides what is required.
        """
        if not self.rating_field:
            return {}
        ratings: dict[str, Any] = {}
        for competency in self.competencies:
            block = result.get(competency.domain_id)
            if not isinstance(block, Mapping):
                continue
            answer = block.get(competency.local_id)
            if isinstance(answer, Mapping) and self.rating_field in answer:
                ratings[competency.id] = answer[self.rating_field]
        return ratings

    def role_of(self, field_id: str) -> FieldRole:
        """What one result field means: its declared role, else ``rating`` or ``other``."""
        declared = self.field_roles.get(field_id)
        if declared is not None:
            return declared
        return "rating" if field_id == self.rating_field else "other"

    def validate_scores(self, scores: Mapping[str, Any]) -> None:
        """Check a competency-to-rating mapping against this framework.

        Raises ``UnknownCompetencyError`` or ``InvalidScoreError``. A rating is
        checked natively: on the scale for ``rag``/``scale``, a number within
        bounds (whole for an ``integer`` step) for ``range``, a true/false for
        ``boolean``. A framework with no declared competencies accepts
        anything, which is what lets a schema-only framework pass through.
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
            {repr(value) for value in scores.values() if not self.rating.accepts(value, self.scale)}
        )
        if off_scale:
            raise InvalidScoreError(
                f"framework {self.id} scores must be {self.rating.describe(self.scale)}; "
                f"got {off_scale}"
            )
