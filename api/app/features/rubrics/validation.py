"""Every rule a version 2 rubric structure must meet before it can be published.

Modelled on `stations/station_validator.py`: one pass over the raw JSON that
collects every problem rather than stopping at the first, each as a
`{path, message}` an author can act on ("sections[2].competencies[0].id"), in
plain language. Every item blocks publishing; `domain.parse_structure` refuses a
structure with any.

The vocabulary (rating kinds, field types, roles, aggregates, tones) and the
size limits live here, in one place. Pure: no I/O.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, TypeGuard

__all__ = [
    "BLOCK_KINDS",
    "DOMAIN_SCORE_AGGREGATES",
    "FEEDBACK_KIND_ROLES",
    "FEEDBACK_SHAPE_TYPES",
    "IDENTIFIER_MESSAGE",
    "IDENTIFIER_PATTERN",
    "SCALE_STEP_TO_V2",
    "SHOW_FROM_V2",
    "SHOW_TO_V2",
    "TOTAL_SCORE_AGGREGATES",
    "is_number",
    "DISPLAY_LABELS",
    "DOMAIN_AGGREGATES",
    "FEEDBACK_KINDS",
    "FEEDBACK_SHAPES",
    "FEEDBACK_SHOW",
    "FEEDBACK_TONES",
    "FIELD_ROLES",
    "FIELD_SOURCES",
    "FIELD_TYPES",
    "MAX_ENUM_VALUES",
    "MAX_MARKED_LEAVES",
    "MAX_NAME_CHARACTERS",
    "MAX_NESTING_DEPTH",
    "MAX_PROPERTIES",
    "RAG_SCALE",
    "RATING_KINDS",
    "RULE_OF",
    "RULE_TYPES",
    "SCALE_STEPS",
    "SCHEMA_VERSION",
    "SCHEME_SHOW",
    "SCHEME_VERSION",
    "SCORE_KINDS",
    "SECTION_KINDS",
    "TONES",
    "TOTAL_AGGREGATES",
    "ValidationError",
    "validate_structure",
]

ValidationError = dict[str, str]

SCHEMA_VERSION = 2
RATING_KINDS = ("rag", "scale", "range", "boolean")
# Best first, as every enumerated scale is written.
RAG_SCALE = ("G", "A", "R")
SECTION_KINDS = ("domain", "section", "field")
FIELD_TYPES = ("rating", "shortText", "longText", "list", "singleSelect", "group", "records")
# What a field is for. Screens read the role, never an exam code or a field id.
FIELD_ROLES = (
    "rating",
    "evidence",
    "explanation",
    "strength",
    "improvement",
    "action",
    "flag",
    "summary",
    "selector",
    "other",
)
FIELD_SOURCES = ("marker", "system")
DOMAIN_AGGREGATES = ("ragCounts", "sum", "mean", "percentAchieved")
TOTAL_AGGREGATES = ("ragShare", "sum", "mean", "percentAchieved")
TONES = ("excellent", "good", "fair", "weak", "poor")
# "title" is legacy: no screen renders it now; kept so stored rubrics that carry it still validate.
DISPLAY_LABELS = ("title", "domainSubtitle", "domainPassLabel", "totalTitle", "trendSubtitle", "passLabel")
# What the candidate's feedback may show or hide, and the wording tone the marker is asked for.
FEEDBACK_SHOW = ("overall", "areaScores", "wentWell", "workOn", "quotes")
FEEDBACK_TONES = ("supportive", "formal", "brief")

# The author's scheme (schemaVersion 3), which compiles to the version 2 above (`scheme.py`).
SCHEME_VERSION = 3
BLOCK_KINDS = ("domain", "notes", "custom")
# The author's words and the version 2 words they compile to; the tuples below are their keys, so the
# two vocabularies cannot drift apart.
FEEDBACK_KIND_ROLES = {
    "strengths": "strength",
    "improvements": "improvement",
    "actions": "action",
    "quotes": "evidence",
    "summary": "summary",
    "flags": "flag",
    "reason": "explanation",
    "note": "other",
}
FEEDBACK_KINDS = tuple(FEEDBACK_KIND_ROLES)
FEEDBACK_SHAPE_TYPES = {"line": "shortText", "paragraph": "longText", "list": "list"}
FEEDBACK_SHAPES = tuple(FEEDBACK_SHAPE_TYPES)
DOMAIN_SCORE_AGGREGATES = {"labels": "ragCounts", "sum": "sum", "mean": "mean", "percent": "percentAchieved"}
TOTAL_SCORE_AGGREGATES = {"labels": "ragShare", "sum": "sum", "mean": "mean", "percent": "percentAchieved"}
SCORE_KINDS = tuple(DOMAIN_SCORE_AGGREGATES)
RULE_TYPES = ("score", "labels")
RULE_OF = ("count", "percent")
SCALE_STEP_TO_V2 = {"whole": "integer", "any": "number"}
SCALE_STEPS = tuple(SCALE_STEP_TO_V2)
SHOW_FROM_V2 = {"areaScores": "domainScores"}
SHOW_TO_V2 = {scheme_key: v2_key for v2_key, scheme_key in SHOW_FROM_V2.items()}
SCHEME_SHOW = tuple(SHOW_FROM_V2.get(key, key) for key in FEEDBACK_SHOW)

# --- Size limits --------------------------------------------------------------
# A structure becomes a strict JSON Schema sent to the model provider, whose
# structured-output mode refuses schemas past these limits (OpenAI's documented
# ones: 10 levels of nesting, 5000 object properties, 1000 enum values, 120,000
# characters of property names and enum values). The leaf cap is about cost and
# marking quality rather than the provider: every leaf is an answer the marker
# writes. Stage 2 of the rubric-templates plan measures it on a real mark per
# exam; the largest platform rubric (SCA) has 112 today.
MAX_NESTING_DEPTH = 10
MAX_PROPERTIES = 5000
MAX_ENUM_VALUES = 1000
MAX_NAME_CHARACTERS = 120_000
MAX_MARKED_LEAVES = 400

# An id is used as a JSON property name and read back by code, so it is
# constrained the way an identifier is rather than left as free text.
IDENTIFIER_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


def validate_structure(raw: Any) -> list[ValidationError]:
    """Every problem with a version 2 structure, in plain language; empty when it can be published."""
    checker = _Checker()
    checker.structure(raw)
    return checker.errors


class _Checker:
    """One validation pass, collecting errors and the sizes the limits are checked against."""

    def __init__(self) -> None:
        """Start with no errors and nothing counted."""
        self.errors: list[ValidationError] = []
        self.properties = 0
        self.enum_values = 0
        self.name_characters = 0
        self.deepest = 0
        self.marked_leaves = 0

    def fail(self, path: str, message: str) -> None:
        """Record one problem at one place in the structure."""
        self.errors.append({"path": path, "message": message})

    # --- The whole structure -------------------------------------------------

    def structure(self, raw: Any) -> None:
        """The root: its version, rating, sections and display, then the size limits."""
        if not isinstance(raw, Mapping):
            self.fail("", "A rubric structure must be an object.")
            return
        if raw.get("schemaVersion") != SCHEMA_VERSION:
            self.fail("schemaVersion", f"This rubric must say schemaVersion {SCHEMA_VERSION}.")
        rating = self.rating(raw.get("rating"))
        sections = raw.get("sections")
        if not isinstance(sections, list) or not sections:
            self.fail("sections", "A rubric needs at least one section: it would ask the marker for nothing.")
            sections = []
        top_level_ids: dict[str, str] = {}
        for index, section in enumerate(sections):
            self.section(section, f"sections[{index}]", rating, top_level_ids)
        self.display(raw.get("display"), rating, sections)
        self.limits()

    def rating(self, raw: Any) -> dict[str, Any]:
        """How every competency is rated. Returns what later rules need (kind, field, scale, bounds)."""
        summary: dict[str, Any] = {"kind": None, "field": None, "scale": (), "minimum": None, "maximum": None}
        if not isinstance(raw, Mapping):
            self.fail("rating", "A rubric needs a rating: how each competency is rated.")
            return summary
        kind = raw.get("kind")
        if kind not in RATING_KINDS:
            self.fail("rating.kind", f"The rating kind must be one of {', '.join(RATING_KINDS)}.")
            return summary
        summary["kind"] = kind
        rating_field = raw.get("field", "score")
        if not isinstance(rating_field, str) or not IDENTIFIER_PATTERN.match(rating_field):
            self.fail("rating.field", IDENTIFIER_MESSAGE)
        else:
            summary["field"] = rating_field
        scale = raw.get("scale")
        if kind == "rag":
            if scale is not None and (not isinstance(scale, list) or sorted(scale) != sorted(RAG_SCALE)):
                self.fail("rating.scale", "An R/A/G rating's scale is G, A and R, each once.")
            summary["scale"] = tuple(scale) if isinstance(scale, list) else RAG_SCALE
        elif kind == "scale":
            values = [str(value) for value in scale] if isinstance(scale, list) else []
            if not values:
                self.fail("rating.scale", "A scale rating needs at least one value.")
            elif len(set(values)) != len(values):
                self.fail("rating.scale", "The scale repeats a value; each must appear once.")
            summary["scale"] = tuple(values)
        elif kind == "range":
            minimum, maximum = raw.get("minimum"), raw.get("maximum")
            if not is_number(minimum) or not is_number(maximum) or not minimum < maximum:
                self.fail("rating", "A range rating needs a minimum below its maximum.")
            else:
                summary["minimum"], summary["maximum"] = minimum, maximum
            if raw.get("step", "number") not in ("number", "integer"):
                self.fail("rating.step", "A range's step must be number or integer.")
        points = raw.get("points")
        if points is not None and kind in ("rag", "scale"):
            if (
                not isinstance(points, list)
                or len(points) != len(summary["scale"])
                or not all(is_number(point) and point >= 0 for point in points)
            ):
                self.fail("rating.points", "Points must give one number for each scale value.")
            elif any(later > earlier for earlier, later in zip(points, points[1:], strict=False)):
                self.fail("rating.points", "Points must not rise down the scale.")
            elif points[0] <= 0:
                self.fail("rating.points", "The best level must earn more than zero points.")
        self.enum_values += len(summary["scale"])
        return summary

    # --- Sections ----------------------------------------------------------------

    def section(self, raw: Any, path: str, rating: Mapping[str, Any], top_level_ids: dict[str, str]) -> None:
        """One domain, written section or lone field, each id used once across the top level."""
        if not isinstance(raw, Mapping):
            self.fail(path, "Each section must be an object.")
            return
        kind = raw.get("kind")
        if kind not in SECTION_KINDS:
            self.fail(f"{path}.kind", f"A section's kind must be one of {', '.join(SECTION_KINDS)}.")
            return
        if kind == "field":
            lone = raw.get("field")
            self.claim_id(
                lone.get("id") if isinstance(lone, Mapping) else None, f"{path}.field", top_level_ids
            )
            self.properties += 1
            self.field(lone, f"{path}.field", depth=2, rating=rating, allow_rating=False)
            return
        section_id = raw.get("id")
        self.claim_id(section_id, path, top_level_ids)
        self.properties += 1
        self.name_characters += len(str(section_id or ""))
        fields = raw.get("fields")
        if kind == "section":
            if not isinstance(fields, list) or not fields:
                self.fail(f"{path}.fields", "A written section needs at least one field.")
            self.field_list(fields, f"{path}.fields", depth=3, rating=rating, taken={})
            return
        self.domain(raw, path, rating)

    def domain(self, raw: Mapping[str, Any], path: str, rating: Mapping[str, Any]) -> None:
        """A rated domain: its competencies, what each answers, and what the domain answers once."""
        competencies = raw.get("competencies")
        if not isinstance(competencies, list) or not competencies:
            self.fail(f"{path}.competencies", "A domain needs at least one competency to rate.")
            competencies = []
        declared_fields = raw.get("competencyFields")
        competency_fields: list[Any] = declared_fields if isinstance(declared_fields, list) else []
        rating_fields = [
            index
            for index, spec in enumerate(competency_fields)
            if isinstance(spec, Mapping) and spec.get("type") == "rating"
        ]
        if len(rating_fields) != 1:
            self.fail(
                f"{path}.competencyFields",
                "A domain rates each competency in exactly one rating field; "
                f"this one has {len(rating_fields)}.",
            )
        elif rating["field"] is not None:
            rated = competency_fields[rating_fields[0]]
            if rated.get("id") != rating["field"]:
                self.fail(
                    f"{path}.competencyFields[{rating_fields[0]}].id",
                    f"The rating field must be called {rating['field']!r}, as the rubric's rating says.",
                )
        # Counted once per competency: every competency answers every one of these.
        before = (self.properties, self.enum_values, self.name_characters, self.marked_leaves)
        self.field_list(
            declared_fields, f"{path}.competencyFields", depth=4, rating=rating, taken={}, allow_rating=True
        )
        per_competency = [
            now - then
            for now, then in zip(
                (self.properties, self.enum_values, self.name_characters, self.marked_leaves),
                before,
                strict=True,
            )
        ]
        extra = max(len(competencies) - 1, 0)
        self.properties += per_competency[0] * extra
        self.enum_values += per_competency[1] * extra
        self.name_characters += per_competency[2] * extra
        self.marked_leaves += per_competency[3] * extra

        taken: dict[str, str] = {}
        scale = set(rating["scale"])
        for index, competency in enumerate(competencies):
            competency_path = f"{path}.competencies[{index}]"
            if not isinstance(competency, Mapping):
                self.fail(competency_path, "Each competency must be an object.")
                continue
            self.claim_id(competency.get("id"), competency_path, taken)
            self.properties += 1
            self.name_characters += len(str(competency.get("id") or ""))
            descriptors = competency.get("descriptors") or {}
            if not isinstance(descriptors, Mapping):
                self.fail(
                    f"{competency_path}.descriptors", "Descriptors must be an object of rating value to text."
                )
            elif rating["kind"] in ("rag", "scale"):
                for value in descriptors:
                    if value not in scale:
                        self.fail(
                            f"{competency_path}.descriptors.{value}",
                            f"{value!r} is not on the rating scale ({', '.join(rating['scale'])}).",
                        )
        self.field_list(raw.get("fields"), f"{path}.fields", depth=3, rating=rating, taken=taken)

    # --- Fields ------------------------------------------------------------------

    def field_list(
        self,
        raw: Any,
        path: str,
        *,
        depth: int,
        rating: Mapping[str, Any],
        taken: dict[str, str],
        allow_rating: bool = False,
    ) -> None:
        """A list of fields at one level, each id used once at that level."""
        if raw is None:
            return
        if not isinstance(raw, list):
            self.fail(path, "Fields must be a list.")
            return
        for index, spec in enumerate(raw):
            field_path = f"{path}[{index}]"
            if isinstance(spec, Mapping):
                self.claim_id(spec.get("id"), field_path, taken)
            self.properties += 1
            self.field(spec, field_path, depth=depth, rating=rating, allow_rating=allow_rating)

    def field(
        self, raw: Any, path: str, *, depth: int, rating: Mapping[str, Any], allow_rating: bool
    ) -> None:
        """One field, checked against its answer format."""
        if not isinstance(raw, Mapping):
            self.fail(path, "Each field must be an object.")
            return
        # The id itself is checked by `claim_id` where the field is listed.
        self.deepest = max(self.deepest, depth)
        self.name_characters += len(str(raw.get("id") or ""))
        field_type = raw.get("type")
        if field_type not in FIELD_TYPES:
            self.fail(f"{path}.type", f"A field's type must be one of {', '.join(FIELD_TYPES)}.")
            return
        if raw.get("role", "other") not in FIELD_ROLES:
            self.fail(f"{path}.role", f"A field's role must be one of {', '.join(FIELD_ROLES)}.")
        if raw.get("source", "marker") not in FIELD_SOURCES:
            self.fail(f"{path}.source", "A field's source must be marker or system.")
        if field_type == "rating" and not allow_rating:
            self.fail(f"{path}.type", "A rating field belongs only in a domain's competency fields.")
        min_items = raw.get("minItems")
        if min_items is not None and (
            not isinstance(min_items, int) or isinstance(min_items, bool) or min_items < 0
        ):
            self.fail(f"{path}.minItems", "minItems must be a whole number, zero or more.")
        if field_type == "singleSelect":
            options = raw.get("options")
            if not isinstance(options, list) or not options:
                self.fail(f"{path}.options", "A single select needs at least one option.")
            else:
                self.enum_values += len(options)
                self.name_characters += sum(len(str(option)) for option in options)
        if field_type in ("group", "records"):
            children = raw.get("fields")
            if not isinstance(children, list) or not children:
                self.fail(f"{path}.fields", f"A {field_type} needs at least one field of its own.")
                return
            self.field_list(children, f"{path}.fields", depth=depth + 1, rating=rating, taken={})
            return
        if raw.get("source", "marker") == "marker":
            self.marked_leaves += 1

    def claim_id(self, identifier: Any, path: str, taken: dict[str, str]) -> None:
        """An id valid as an identifier and not already used at this level."""
        if not isinstance(identifier, str) or not IDENTIFIER_PATTERN.match(identifier):
            self.fail(f"{path}.id", IDENTIFIER_MESSAGE)
            return
        if identifier in taken:
            self.fail(
                f"{path}.id", f"{identifier!r} is already used by {taken[identifier]}; ids must differ."
            )
            return
        taken[identifier] = path

    # --- Display -----------------------------------------------------------------

    def rule_matches_rating(
        self, part: str, node: Mapping[str, Any], rule: Mapping[str, Any], rating: Mapping[str, Any]
    ) -> None:
        """A pass rule that counts ratings names a level this rating has, and counts them the way it says."""
        path = f"display.{part}.rule"
        if rule["type"] == "score":
            if node.get("aggregate") in ("ragCounts", "ragShare"):
                self.fail(path, "A count of ratings passes on a count rule, not a score to reach.")
            return
        if rule.get("of") not in RULE_OF:
            self.fail(f"{path}.of", "Count competencies, or a percentage of them.")
        elif rule["of"] == "percent" and rule["atLeast"] > 100:
            self.fail(f"{path}.atLeast", "A percentage is at most 100.")
        value, kind = rule.get("value"), rating.get("kind")
        if kind in ("rag", "scale"):
            known = isinstance(value, str) and value in rating["scale"]
        elif kind == "boolean":
            known = isinstance(value, bool)
        else:
            low, high = rating.get("minimum"), rating.get("maximum")
            known = is_number(value) and is_number(low) and is_number(high) and low <= value <= high
        if kind is not None and not known:
            self.fail(f"{path}.value", "The rule names a level the scale does not have.")

    def display(self, raw: Any, rating: Mapping[str, Any], sections: list[Any]) -> None:
        """How feedback and the dashboard read the rubric: known words, and lines inside the range."""
        if raw is None:
            return
        if not isinstance(raw, Mapping):
            self.fail("display", "The display settings must be an object.")
            return
        domain = raw.get("domain") or {}
        total = raw.get("total") or {}
        if not isinstance(domain, Mapping) or not isinstance(total, Mapping):
            self.fail("display", "display.domain and display.total must be objects.")
            return
        if domain.get("aggregate") is not None and domain["aggregate"] not in DOMAIN_AGGREGATES:
            self.fail(
                "display.domain.aggregate", f"A domain aggregate is one of {', '.join(DOMAIN_AGGREGATES)}."
            )
        if total.get("aggregate") is not None and total["aggregate"] not in TOTAL_AGGREGATES:
            self.fail(
                "display.total.aggregate", f"A total aggregate is one of {', '.join(TOTAL_AGGREGATES)}."
            )
        for part, node in (("domain", domain), ("total", total)):
            rule = node.get("rule")
            if rule is None:
                continue
            if (
                not isinstance(rule, Mapping)
                or rule.get("type") not in RULE_TYPES
                or not is_number(rule.get("atLeast"))
                or rule["atLeast"] < 0
            ):
                self.fail(f"display.{part}.rule", "A pass rule needs a type and a number to reach.")
            elif node.get("passAtLeast") is not None:
                self.fail(f"display.{part}.rule", "Set a pass line or a pass rule, not both.")
            else:
                self.rule_matches_rating(part, node, rule, rating)
        for key in ("passAtLeast",):
            if domain.get(key) is not None and (not is_number(domain[key]) or domain[key] < 0):
                self.fail(f"display.domain.{key}", "A domain pass line must be a number, zero or more.")
        for key in ("max", "passAtLeast"):
            if total.get(key) is not None and (not is_number(total[key]) or total[key] < 0):
                self.fail(
                    f"display.total.{key}", "A total's max and pass line must be numbers, zero or more."
                )
        if (
            is_number(total.get("max"))
            and is_number(total.get("passAtLeast"))
            and total["passAtLeast"] > total["max"]
        ):
            self.fail("display.total.passAtLeast", "The pass line sits above the total's maximum.")
        if (
            total.get("requireEveryDomain")
            and domain.get("passAtLeast") is None
            and domain.get("rule") is None
        ):
            self.fail(
                "display.total.requireEveryDomain",
                "Requiring every domain to pass needs a domain pass line (display.domain.passAtLeast).",
            )
        maximum = rating.get("maximum")
        if (
            domain.get("aggregate") == "mean"
            and is_number(domain.get("passAtLeast"))
            and is_number(maximum)
            and domain["passAtLeast"] > maximum
        ):
            self.fail(
                "display.domain.passAtLeast",
                f"The domain pass line sits above the rating's maximum ({maximum}).",
            )
        tones = raw.get("tones")
        if tones is not None:
            if rating["kind"] in ("rag", "scale"):
                self.fail(
                    "display.tones",
                    "A scale rating is coloured by each value's place on the scale; remove tones.",
                )
            elif not isinstance(tones, list):
                self.fail("display.tones", "Tones must be a list.")
            else:
                for index, tone in enumerate(tones):
                    tone_path = f"display.tones[{index}]"
                    if not isinstance(tone, Mapping):
                        self.fail(tone_path, "Each tone must be an object.")
                        continue
                    at_least = tone.get("atLeast")
                    if not is_number(at_least) or not 0 <= at_least <= 1:
                        self.fail(
                            f"{tone_path}.atLeast",
                            "atLeast is a fraction of the rating's maximum, from 0 to 1.",
                        )
                    self.tone(tone.get("tone"), f"{tone_path}.tone")
        bands = raw.get("bands")
        if bands is not None:
            if not isinstance(bands, list):
                self.fail("display.bands", "Bands must be a list.")
            else:
                for index, band in enumerate(bands):
                    band_path = f"display.bands[{index}]"
                    if not isinstance(band, Mapping):
                        self.fail(band_path, "Each band must be an object.")
                        continue
                    start, end = band.get("from"), band.get("to")
                    if not is_number(start) or not is_number(end) or start > end:
                        self.fail(band_path, "A band needs a from no greater than its to.")
                    elif is_number(total.get("max")) and end > total["max"]:
                        self.fail(f"{band_path}.to", "A band ends above the total's maximum.")
                    if not isinstance(band.get("label", ""), str):
                        self.fail(f"{band_path}.label", "A band's label must be text.")
                    self.tone(band.get("tone"), f"{band_path}.tone")
        self.feedback_display(raw)
        labels = raw.get("labels")
        if labels is not None:
            if not isinstance(labels, Mapping):
                self.fail("display.labels", "Labels must be an object of name to text.")
            else:
                for key, value in labels.items():
                    if key not in DISPLAY_LABELS:
                        self.fail(
                            f"display.labels.{key}",
                            f"Unknown label; the labels are {', '.join(DISPLAY_LABELS)}.",
                        )
                    elif not isinstance(value, str):
                        self.fail(f"display.labels.{key}", "A label must be text.")

    def feedback_display(self, raw: Mapping[str, Any]) -> None:
        """Which feedback fields the candidate sees, and the tone the marker writes in."""
        tone = raw.get("feedbackTone")
        if tone is not None and tone not in FEEDBACK_TONES:
            self.fail("display.feedbackTone", f"A feedback tone is one of {', '.join(FEEDBACK_TONES)}.")
        show = raw.get("show")
        if show is None:
            return
        if not isinstance(show, Mapping):
            self.fail("display.show", "Shown fields must be an object of field to true or false.")
            return
        for key, value in show.items():
            if key not in FEEDBACK_SHOW:
                self.fail(f"display.show.{key}", f"Unknown field; the fields are {', '.join(FEEDBACK_SHOW)}.")
            elif not isinstance(value, bool):
                self.fail(f"display.show.{key}", "Shown or hidden must be true or false.")

    def tone(self, tone: Any, path: str) -> None:
        """A colour from the few the screens draw."""
        if tone not in TONES:
            self.fail(path, f"A tone is one of {', '.join(TONES)}.")

    # --- Size ----------------------------------------------------------------------

    def limits(self) -> None:
        """What the model provider accepts, and what a mark can afford."""
        if self.deepest > MAX_NESTING_DEPTH:
            self.fail(
                "sections",
                f"Fields nest {self.deepest} levels deep; the most a marker can fill is {MAX_NESTING_DEPTH}.",
            )
        if self.properties > MAX_PROPERTIES:
            self.fail(
                "sections",
                f"The result has {self.properties} properties; the most allowed is {MAX_PROPERTIES}.",
            )
        if self.enum_values > MAX_ENUM_VALUES:
            self.fail(
                "sections",
                f"The result has {self.enum_values} choice values; the most allowed is {MAX_ENUM_VALUES}.",
            )
        if self.name_characters > MAX_NAME_CHARACTERS:
            self.fail(
                "sections",
                f"Ids and choices add up to {self.name_characters} characters; "
                f"the most allowed is {MAX_NAME_CHARACTERS}.",
            )
        if self.marked_leaves > MAX_MARKED_LEAVES:
            self.fail(
                "sections",
                f"The marker would write {self.marked_leaves} answers; "
                f"the most allowed is {MAX_MARKED_LEAVES}. "
                f"Remove {self.marked_leaves - MAX_MARKED_LEAVES} "
                "(fewer competencies, or fewer fields per competency).",
            )


IDENTIFIER_MESSAGE = (
    "An id uses lower-case letters, digits and underscores, starts with a letter, and is at most 64 long."
)


def is_number(value: object) -> TypeGuard[int | float]:
    """A real number, not text and not a boolean passed off as one."""
    return isinstance(value, int | float) and not isinstance(value, bool)
