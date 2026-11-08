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
            self.fail(
                "", "This marking scheme could not be read, so it cannot be used. Check it and try again."
            )
            return
        if raw.get("schemaVersion") != SCHEMA_VERSION:
            self.fail(
                "schemaVersion",
                "This marking scheme is in an old or unknown format. Open it in the marking scheme builder "
                "and save it again.",
            )
        rating = self.rating(raw.get("rating"))
        sections = raw.get("sections")
        if not isinstance(sections, list) or not sections:
            self.fail(
                "sections", "Add at least one Domain or section, otherwise the marker has nothing to mark."
            )
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
            self.fail(
                "rating",
                "Add a rating scale so markers know how to rate each Competency, for example Good, Fair "
                "and Poor.",
            )
            return summary
        kind = raw.get("kind")
        if kind not in RATING_KINDS:
            self.fail(
                "rating.kind",
                "Choose how Competencies are rated: red, amber and green; named levels such as Good and "
                "Fair; a number range; or yes and no.",
            )
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
                self.fail(
                    "rating.scale",
                    "A red, amber and green rating must use Green, Amber and Red (G, A and R), each once.",
                )
            summary["scale"] = tuple(scale) if isinstance(scale, list) else RAG_SCALE
        elif kind == "scale":
            values = [str(value) for value in scale] if isinstance(scale, list) else []
            if not values:
                self.fail("rating.scale", "A rating scale needs at least one level, such as Good.")
            elif len(set(values)) != len(values):
                self.fail(
                    "rating.scale",
                    "A level appears twice on the rating scale. Each level can appear only once.",
                )
            summary["scale"] = tuple(values)
        elif kind == "range":
            minimum, maximum = raw.get("minimum"), raw.get("maximum")
            if not is_number(minimum) or not is_number(maximum) or not minimum < maximum:
                self.fail(
                    "rating",
                    "A number range needs a lowest number that is smaller than the highest, for example 1 "
                    "to 5.",
                )
            else:
                summary["minimum"], summary["maximum"] = minimum, maximum
            if raw.get("step", "number") not in ("number", "integer"):
                self.fail(
                    "rating.step",
                    "Choose whether markers give any number, including decimals, or whole numbers only.",
                )
        points = raw.get("points")
        if points is not None and kind in ("rag", "scale"):
            if (
                not isinstance(points, list)
                or len(points) != len(summary["scale"])
                or not all(is_number(point) and point >= 0 for point in points)
            ):
                self.fail("rating.points", "Give each level on the rating scale its own points, as a number.")
            elif any(later > earlier for earlier, later in zip(points, points[1:], strict=False)):
                self.fail(
                    "rating.points",
                    "A lower level cannot earn more points than the one above it. List the best level "
                    "first, for example Good, then Fair, then Poor.",
                )
            elif points[0] <= 0:
                self.fail("rating.points", "The best level, such as Good, must earn more than 0 points.")
        self.enum_values += len(summary["scale"])
        return summary

    # --- Sections ----------------------------------------------------------------

    def section(self, raw: Any, path: str, rating: Mapping[str, Any], top_level_ids: dict[str, str]) -> None:
        """One domain, written section or lone field, each id used once across the top level."""
        if not isinstance(raw, Mapping):
            self.fail(path, "This section is not set up correctly. Remove it and add it again.")
            return
        kind = raw.get("kind")
        if kind not in SECTION_KINDS:
            self.fail(
                f"{path}.kind",
                "Each part of the marking scheme must be a Domain, a written section or a single question.",
            )
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
                self.fail(
                    f"{path}.fields",
                    "A written section needs at least one question for the marker to answer.",
                )
            self.field_list(fields, f"{path}.fields", depth=3, rating=rating, taken={})
            return
        self.domain(raw, path, rating)

    def domain(self, raw: Mapping[str, Any], path: str, rating: Mapping[str, Any]) -> None:
        """A rated domain: its competencies, what each answers, and what the domain answers once."""
        competencies = raw.get("competencies")
        if not isinstance(competencies, list) or not competencies:
            self.fail(f"{path}.competencies", "Add at least one Competency to this Domain.")
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
                "Each Domain needs exactly one rating for its Competencies; "
                f"this one has {len(rating_fields)}.",
            )
        elif rating["field"] is not None:
            rated = competency_fields[rating_fields[0]]
            if rated.get("id") != rating["field"]:
                self.fail(
                    f"{path}.competencyFields[{rating_fields[0]}].id",
                    f"The rating in this Domain must use the same name as the marking scheme's rating, "
                    f"which is {rating['field']!r}.",
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
                self.fail(
                    competency_path, "This Competency is not set up correctly. Remove it and add it again."
                )
                continue
            self.claim_id(competency.get("id"), competency_path, taken)
            self.properties += 1
            self.name_characters += len(str(competency.get("id") or ""))
            descriptors = competency.get("descriptors") or {}
            if not isinstance(descriptors, Mapping):
                self.fail(
                    f"{competency_path}.descriptors",
                    "The descriptions for each level are not set up correctly. Write one short description "
                    "per level.",
                )
            elif rating["kind"] in ("rag", "scale"):
                for value in descriptors:
                    if value not in scale:
                        self.fail(
                            f"{competency_path}.descriptors.{value}",
                            f"The description for {value!r} does not match a level on the rating scale "
                            f"({', '.join(rating['scale'])}). Use one of those levels, or remove it.",
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
            self.fail(
                path, "The questions in this part are not set up correctly. Remove them and add them again."
            )
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
            self.fail(path, "This question is not set up correctly. Remove it and add it again.")
            return
        # The id itself is checked by `claim_id` where the field is listed.
        self.deepest = max(self.deepest, depth)
        self.name_characters += len(str(raw.get("id") or ""))
        field_type = raw.get("type")
        if field_type not in FIELD_TYPES:
            self.fail(
                f"{path}.type",
                "Choose what kind of answer this question needs, such as short text, long text, a list or "
                "a choice.",
            )
            return
        if raw.get("role", "other") not in FIELD_ROLES:
            self.fail(f"{path}.role", "Choose what this question is used for.")
        if raw.get("source", "marker") not in FIELD_SOURCES:
            self.fail(f"{path}.source", "Choose who fills this in: the marker or the system.")
        if field_type == "rating" and not allow_rating:
            self.fail(f"{path}.type", "A rating can only be added to a Competency inside a Domain.")
        min_items = raw.get("minItems")
        if min_items is not None and (
            not isinstance(min_items, int) or isinstance(min_items, bool) or min_items < 0
        ):
            self.fail(f"{path}.minItems", "The minimum number of entries must be a whole number, 0 or more.")
        if field_type == "singleSelect":
            options = raw.get("options")
            if not isinstance(options, list) or not options:
                self.fail(f"{path}.options", "A question with a list of choices needs at least one choice.")
            else:
                self.enum_values += len(options)
                self.name_characters += sum(len(str(option)) for option in options)
        if field_type in ("group", "records"):
            children = raw.get("fields")
            if not isinstance(children, list) or not children:
                self.fail(f"{path}.fields", "A grouped question needs at least one question inside it.")
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
                f"{path}.id",
                f"The name {identifier!r} is already used in this list. Give each item its own name.",
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
                self.fail(
                    path,
                    "When you count ratings, say how many must reach a level, rather than setting a score "
                    "to reach.",
                )
            return
        if rule.get("of") not in RULE_OF:
            self.fail(
                f"{path}.of",
                "Choose whether the pass mark is a number of Competencies or a percentage of them.",
            )
        elif rule["of"] == "percent" and rule["atLeast"] > 100:
            self.fail(f"{path}.atLeast", "A percentage cannot be more than 100.")
        value, kind = rule.get("value"), rating.get("kind")
        if kind in ("rag", "scale"):
            known = isinstance(value, str) and value in rating["scale"]
        elif kind == "boolean":
            known = isinstance(value, bool)
        else:
            low, high = rating.get("minimum"), rating.get("maximum")
            known = is_number(value) and is_number(low) and is_number(high) and low <= value <= high
        if kind is not None and not known:
            self.fail(
                f"{path}.value",
                "The pass mark uses a level that is not on the rating scale. Choose one of its levels, "
                "such as Good or Fair.",
            )

    def display(self, raw: Any, rating: Mapping[str, Any], sections: list[Any]) -> None:
        """How feedback and the dashboard read the rubric: known words, and lines inside the range."""
        if raw is None:
            return
        if not isinstance(raw, Mapping):
            self.fail("display", "The feedback display settings are not set up correctly.")
            return
        domain = raw.get("domain") or {}
        total = raw.get("total") or {}
        if not isinstance(domain, Mapping) or not isinstance(total, Mapping):
            self.fail("display", "The Domain and total display settings are not set up correctly.")
            return
        if domain.get("aggregate") is not None and domain["aggregate"] not in DOMAIN_AGGREGATES:
            self.fail(
                "display.domain.aggregate",
                "Choose how each Domain's score is worked out: add up, average, percentage or count of "
                "ratings.",
            )
        if total.get("aggregate") is not None and total["aggregate"] not in TOTAL_AGGREGATES:
            self.fail(
                "display.total.aggregate",
                "Choose how the total score is worked out: add up, average, percentage or share of ratings.",
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
                self.fail(
                    f"display.{part}.rule",
                    "A pass mark needs a type (a score or a count of ratings) and a number to reach.",
                )
            elif node.get("passAtLeast") is not None:
                self.fail(f"display.{part}.rule", "Set either a pass mark or a pass rule, not both.")
            else:
                self.rule_matches_rating(part, node, rule, rating)
        for key in ("passAtLeast",):
            if domain.get(key) is not None and (not is_number(domain[key]) or domain[key] < 0):
                self.fail(f"display.domain.{key}", "A Domain's pass mark must be a number, 0 or more.")
        for key in ("max", "passAtLeast"):
            if total.get(key) is not None and (not is_number(total[key]) or total[key] < 0):
                self.fail(
                    f"display.total.{key}",
                    "The total marks and the overall pass mark must be numbers, 0 or more.",
                )
        if (
            is_number(total.get("max"))
            and is_number(total.get("passAtLeast"))
            and total["passAtLeast"] > total["max"]
        ):
            self.fail(
                "display.total.passAtLeast",
                "The overall pass mark is higher than the most marks anyone can get. Lower it.",
            )
        if (
            total.get("requireEveryDomain")
            and domain.get("passAtLeast") is None
            and domain.get("rule") is None
        ):
            self.fail(
                "display.total.requireEveryDomain",
                "To require every Domain to pass, set a pass mark for each Domain first.",
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
                f"A Domain's pass mark is higher than the highest rating ({maximum}). Lower it.",
            )
        tones = raw.get("tones")
        if tones is not None:
            if rating["kind"] in ("rag", "scale"):
                self.fail(
                    "display.tones",
                    "Named levels are coloured automatically by their place on the scale, so remove the "
                    "custom colours.",
                )
            elif not isinstance(tones, list):
                self.fail(
                    "display.tones",
                    "The score colours are not set up correctly. Remove them and add them again.",
                )
            else:
                for index, tone in enumerate(tones):
                    tone_path = f"display.tones[{index}]"
                    if not isinstance(tone, Mapping):
                        self.fail(
                            tone_path,
                            "This score colour is not set up correctly. Remove it and add it again.",
                        )
                        continue
                    at_least = tone.get("atLeast")
                    if not is_number(at_least) or not 0 <= at_least <= 1:
                        self.fail(
                            f"{tone_path}.atLeast",
                            "A colour starts at a share of the highest rating, from 0 (none of it) to 1 "
                            "(all of it).",
                        )
                    self.tone(tone.get("tone"), f"{tone_path}.tone")
        bands = raw.get("bands")
        if bands is not None:
            if not isinstance(bands, list):
                self.fail(
                    "display.bands",
                    "The score bands are not set up correctly. Remove them and add them again.",
                )
            else:
                for index, band in enumerate(bands):
                    band_path = f"display.bands[{index}]"
                    if not isinstance(band, Mapping):
                        self.fail(
                            band_path, "This score band is not set up correctly. Remove it and add it again."
                        )
                        continue
                    start, end = band.get("from"), band.get("to")
                    if not is_number(start) or not is_number(end) or start > end:
                        self.fail(band_path, "A score band must start at or below the number where it ends.")
                    elif is_number(total.get("max")) and end > total["max"]:
                        self.fail(
                            f"{band_path}.to", "A score band ends above the highest possible total. Lower it."
                        )
                    if not isinstance(band.get("label", ""), str):
                        self.fail(f"{band_path}.label", "A score band's name must be text.")
                    self.tone(band.get("tone"), f"{band_path}.tone")
        self.feedback_display(raw)
        labels = raw.get("labels")
        if labels is not None:
            if not isinstance(labels, Mapping):
                self.fail("display.labels", "The custom wording is not set up correctly.")
            else:
                for key, value in labels.items():
                    if key not in DISPLAY_LABELS:
                        self.fail(
                            f"display.labels.{key}",
                            "This wording cannot be changed.",
                        )
                    elif not isinstance(value, str):
                        self.fail(f"display.labels.{key}", "Custom wording must be text.")

    def feedback_display(self, raw: Mapping[str, Any]) -> None:
        """Which feedback fields the candidate sees, and the tone the marker writes in."""
        tone = raw.get("feedbackTone")
        if tone is not None and tone not in FEEDBACK_TONES:
            self.fail("display.feedbackTone", "Choose a tone for the feedback: supportive, formal or brief.")
        show = raw.get("show")
        if show is None:
            return
        if not isinstance(show, Mapping):
            self.fail("display.show", "The shown and hidden feedback settings are not set up correctly.")
            return
        for key, value in show.items():
            if key not in FEEDBACK_SHOW:
                self.fail(f"display.show.{key}", "This part of the feedback cannot be shown or hidden.")
            elif not isinstance(value, bool):
                self.fail(f"display.show.{key}", "Choose Shown or Hidden.")

    def tone(self, tone: Any, path: str) -> None:
        """A colour from the few the screens draw."""
        if tone not in TONES:
            self.fail(path, f"Choose a colour: {', '.join(TONES)}.")

    # --- Size ----------------------------------------------------------------------

    def limits(self) -> None:
        """What the model provider accepts, and what a mark can afford."""
        if self.deepest > MAX_NESTING_DEPTH:
            self.fail(
                "sections",
                f"Questions sit {self.deepest} levels deep inside each other; the most allowed is "
                f"{MAX_NESTING_DEPTH}. Move some questions out.",
            )
        if self.properties > MAX_PROPERTIES:
            self.fail(
                "sections",
                f"This marking scheme has too many items ({self.properties}; the most allowed is "
                f"{MAX_PROPERTIES}). Remove some Competencies or questions.",
            )
        if self.enum_values > MAX_ENUM_VALUES:
            self.fail(
                "sections",
                f"This marking scheme has too many choices ({self.enum_values}; the most allowed is "
                f"{MAX_ENUM_VALUES}). Remove some choices or levels.",
            )
        if self.name_characters > MAX_NAME_CHARACTERS:
            self.fail(
                "sections",
                f"The names and choices are too long in total ({self.name_characters} characters; "
                f"the most allowed is {MAX_NAME_CHARACTERS}). Shorten some or remove some.",
            )
        if self.marked_leaves > MAX_MARKED_LEAVES:
            self.fail(
                "sections",
                f"The marker would have to give {self.marked_leaves} answers; "
                f"the most allowed is {MAX_MARKED_LEAVES}. "
                f"Remove {self.marked_leaves - MAX_MARKED_LEAVES} "
                "(use fewer Competencies, or fewer questions per Competency).",
            )


IDENTIFIER_MESSAGE = (
    "Use a short name of lower-case letters, numbers and underscores, "
    "starting with a letter and at most 64 characters, for example history_taking."
)


def is_number(value: object) -> TypeGuard[int | float]:
    """A real number, not text and not a boolean passed off as one."""
    return isinstance(value, int | float) and not isinstance(value, bool)
