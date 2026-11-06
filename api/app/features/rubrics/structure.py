"""The shape every reader gets (structure schemaVersion 2). A stored v3 scheme compiles to this.

Its own module because both halves of this slice need it: `domain.py` parses a
stored structure into these, and `schema_builder.py` turns them into the JSON
Schema a marker fills. Neither may import the other.

A rubric is a template, the way a station template is. It has one `rating` (how
every competency is rated), an ordered list of `sections`, and an optional
`display` (how feedback and the dashboard read it). A section is one of:

- a *domain*: competencies that are rated, the fields every competency answers
  (`competency_fields`, one of which holds the rating) and any fields the
  domain answers once (`fields`);
- a *section*: a group of written fields nobody rates;
- a *field*: one written field that sits at the top of the result on its own
  (Ortho's `station_type`, a v1 rubric's `actionable_feedback` list).

Every field has an answer format (`type`), a `role` the screens read instead of
an exam code, and the `instructions` the marker reads for it. The plan this
follows is `docs/plans/rubric-templates.md` §3 and §4.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "NO_DEFAULT",
    "CompetencySpec",
    "DisplayBand",
    "DisplayDomain",
    "DisplaySpec",
    "DisplayTone",
    "DisplayTotal",
    "FieldSpec",
    "InvalidRubric",
    "RatingSpec",
    "RubricStructure",
    "SectionSpec",
]


class InvalidRubric(ValueError):
    """A structure that cannot be marked against. The service maps this to 422."""


class _NoDefault:
    """Marks a field with no `default`, which is different from a default of null."""

    def __repr__(self) -> str:
        """Readable in a failing assertion."""
        return "NO_DEFAULT"


NO_DEFAULT: Any = _NoDefault()


@dataclass(frozen=True)
class RatingSpec:
    """How every competency in the rubric is rated, in the exam's own units.

    `rag` and `scale` rate on a list of words (`scale`, best first); `range` on
    a number from `minimum` to `maximum`, whole when `step` is `integer`;
    `boolean` on competent or not. `field` is the competency field that holds
    the rating (`score` for most exams, `competent` for CASC).
    """

    kind: str
    field: str = "score"
    scale: tuple[str, ...] = ()
    minimum: float | None = None
    maximum: float | None = None
    step: str = "number"
    # Points per scale value, best first; None means n..1 (the position).
    points: tuple[float, ...] | None = None

    @property
    def is_enumerated(self) -> bool:
        """Whether a rating is one of a fixed list of values."""
        return self.kind in ("rag", "scale")

    def points_for(self, value: Any) -> float | None:
        """The points an enumerated value earns, or None when the rating has none (n..1 by position)."""
        if self.points and self.is_enumerated and value in self.scale:
            return float(self.points[self.scale.index(value)])
        return None


@dataclass(frozen=True)
class FieldSpec:
    """One thing a result holds: its answer format, role, instructions and who writes it."""

    id: str
    type: str
    label: str = ""
    required: bool = True
    instructions: str = ""
    role: str = "other"
    # `marker` fields are asked of the marker. `system` fields are written by
    # the platform (e.g. what a live panel showed) and only appear in the
    # display schema that stored results are checked against.
    source: str = "marker"
    nullable: bool = False
    default: Any = NO_DEFAULT
    # An illustration the model reads beside the instructions.
    example: Any = None
    min_items: int | None = None
    # A `singleSelect`'s choices.
    options: tuple[str, ...] = ()
    # A `group`'s, or each `records` entry's, own fields.
    fields: tuple[FieldSpec, ...] = ()


@dataclass(frozen=True)
class CompetencySpec:
    """One skill a candidate is rated on, within a domain."""

    id: str
    label: str
    # What the marker looks for, verbatim. Optional.
    instructions: str = ""
    # What earns each rating value, keyed by value. Optional: a rubric may name
    # a competency without spelling out its anchors.
    descriptors: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SectionSpec:
    """One part of the result: a rated domain, a written section, or a lone top-level field."""

    id: str
    title: str
    # "domain", "section" or "field" (see the module docstring).
    kind: str
    # What this part assesses or asks for, read by the marker.
    instructions: str = ""
    # Whether this domain can be judged while the consultation is still running.
    live: bool = False
    # Whether the result may leave this part null (Ortho fills only the
    # station's own domain).
    nullable: bool = False
    # Read beside `nullable`: what the part is, said on the nullable wrapper
    # (Ortho's "Clinical station feedback (Station 2)"). Only used when nullable.
    description: str = ""
    required: bool = True
    competencies: tuple[CompetencySpec, ...] = ()
    # What every competency in the domain answers (the rating and its evidence).
    competency_fields: tuple[FieldSpec, ...] = ()
    # What the domain or section answers once; for a lone field, that field.
    fields: tuple[FieldSpec, ...] = ()


@dataclass(frozen=True)
class DisplayDomain:
    """How a domain's score is aggregated, and where its pass line sits."""

    aggregate: str | None = None
    pass_at_least: float | None = None
    # A v3 pass rule; replaces pass_at_least when set.
    rule: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class DisplayTotal:
    """How a station's total is aggregated and judged."""

    aggregate: str | None = None
    maximum: float | None = None
    pass_at_least: float | None = None
    # Pass also needs every domain at or above the domain pass line (PLAB 2).
    require_every_domain: bool = False
    # A v3 pass rule; replaces pass_at_least when set.
    rule: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class DisplayTone:
    """A colour for a rating, from a fraction of the rating's maximum upwards."""

    at_least: float
    tone: str


@dataclass(frozen=True)
class DisplayBand:
    """A named band of the station total, e.g. 35 to 42 is "good"."""

    start: float
    end: float
    label: str
    tone: str


@dataclass(frozen=True)
class DisplaySpec:
    """How feedback and the dashboard read this rubric. Every part is optional."""

    domain: DisplayDomain = field(default_factory=DisplayDomain)
    total: DisplayTotal = field(default_factory=DisplayTotal)
    tones: tuple[DisplayTone, ...] = ()
    bands: tuple[DisplayBand, ...] = ()
    labels: Mapping[str, str] = field(default_factory=dict)
    # Feedback fields the author hid from the candidate (`overall`, `areaScores`, ...); absent means shown.
    show: Mapping[str, bool] = field(default_factory=dict)
    # The marker's tone: `supportive`, `formal` or `brief`; None leaves the prompt as written.
    feedback_tone: str | None = None


@dataclass(frozen=True)
class RubricStructure:
    """A whole authored rubric: its rating, its ordered sections and its display."""

    rating: RatingSpec
    sections: tuple[SectionSpec, ...]
    display: DisplaySpec = field(default_factory=DisplaySpec)
    # What the whole result is, read by the marker as the schema's description.
    instructions: str = ""

    @property
    def domains(self) -> tuple[SectionSpec, ...]:
        """The rated sections, in authored order."""
        return tuple(section for section in self.sections if section.kind == "domain")

    @property
    def scale(self) -> tuple[str, ...]:
        """The rating's values when it is enumerated; empty for a range or boolean."""
        return self.rating.scale if self.rating.is_enumerated else ()

    @property
    def competencies(self) -> tuple[CompetencySpec, ...]:
        """Every competency across every domain, flattened."""
        return tuple(competency for domain in self.domains for competency in domain.competencies)
