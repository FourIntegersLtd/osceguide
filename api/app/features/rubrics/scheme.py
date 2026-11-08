"""The author's marking scheme (schemaVersion 3), and how it compiles to the version 2 readers mark against.

Pure: no I/O. A stored row is never rewritten; see `domain.upgrade_structure`.

A scheme is five blocks an author understands (domain, competency, scale,
pass rule, feedback). `upgrade_v2_to_v3` reads a version 2 structure as a
scheme and `compile_v3` writes it back, key for key, so a scheme upgraded from
a stored rubric marks exactly as that rubric did. Anything the blocks cannot
hold stays raw: inside a block's `advanced`, as a `custom` item, or, when the
whole structure is odd, as `advanced.raw`.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from typing import Any

from app.features.rubrics import validation

__all__ = [
    "BOOLEAN_LEVELS",
    "RAG_LEVELS",
    "compile_v3",
    "scheme_path",
    "upgrade_v2_to_v3",
    "validate_scheme",
]

# The vocabularies live in `validation.py` (it validates the author's words and cannot import this
# module); here they are read in both directions.
_KIND_TO_ROLE = validation.FEEDBACK_KIND_ROLES
_ROLE_TO_KIND = {role: kind for kind, role in _KIND_TO_ROLE.items()}
_SHAPE_TO_TYPE = validation.FEEDBACK_SHAPE_TYPES
_TYPE_TO_SHAPE = {field_type: shape for shape, field_type in _SHAPE_TO_TYPE.items()}
_AGGREGATE_TO_SCORE = {
    aggregate: score
    for table in (validation.DOMAIN_SCORE_AGGREGATES, validation.TOTAL_SCORE_AGGREGATES)
    for score, aggregate in table.items()
}
_STEP_TO_V2 = validation.SCALE_STEP_TO_V2
_STEP_FROM_V2 = {v2_step: step for step, v2_step in _STEP_TO_V2.items()}

# What an item copies when the v2 field has it, and what it keeps aside in its own `advanced`.
_ITEM_KEYS = ("label", "instructions", "required", "example", "minItems")
_ITEM_EXTRA_KEYS = ("nullable", "default", "source")

RAG_LEVELS: list[dict[str, Any]] = [
    {"value": "G", "label": "Green", "points": 3},
    {"value": "A", "label": "Amber", "points": 2},
    {"value": "R", "label": "Red", "points": 1},
]
BOOLEAN_LEVELS: list[dict[str, Any]] = [
    {"value": True, "label": "Competent", "points": 1},
    {"value": False, "label": "Not competent", "points": 0},
]

_TOP_LEVEL_KEYS = ("schemaVersion", "instructions", "rating", "sections", "display", "basedOn")
_DOMAIN_KEYS = (
    "kind",
    "id",
    "title",
    "instructions",
    "live",
    "nullable",
    "description",
    "competencies",
    "competencyFields",
    "fields",
)
_SECTION_KEYS = ("kind", "id", "title", "instructions", "fields")
_DISPLAY_KEYS = ("domain", "total", "tones", "bands", "labels", "show", "feedbackTone")

_NOT_A_SCHEME = "A marking scheme must be an object."


# --- Version 2 -> the author's scheme -------------------------------------------------


def upgrade_v2_to_v3(raw: Mapping[str, Any]) -> dict[str, Any]:
    """A version 2 structure as the author's scheme; never raises, keeps what the blocks cannot hold raw."""
    source = copy.deepcopy(dict(raw))
    candidate: dict[str, Any] | None
    try:
        candidate = _upgrade(source)
    except (TypeError, ValueError, KeyError, AttributeError, IndexError):
        candidate = None
    if candidate is None or compile_v3(candidate) != source:
        fallback: dict[str, Any] = {"schemaVersion": validation.SCHEME_VERSION, "advanced": {"raw": source}}
        if "basedOn" in source:
            fallback["basedOn"] = copy.deepcopy(source["basedOn"])
        return fallback
    return candidate


def _upgrade(raw: dict[str, Any]) -> dict[str, Any]:
    """The candidate scheme for a version 2 structure; the caller checks it compiles back."""
    rating = raw["rating"]
    sections = raw["sections"]
    if not isinstance(rating, Mapping) or not isinstance(sections, list):
        raise TypeError("rating and sections must be an object and a list")
    advanced: dict[str, Any] = {}
    scale = _scale_from_rating(rating, advanced)
    levels = scale.get("levels") or []
    out: dict[str, Any] = {"schemaVersion": validation.SCHEME_VERSION}
    if "instructions" in raw:
        out["instructions"] = raw["instructions"]
    hoisted = _hoisted_fields(sections, rating)
    out["mark"] = {"field": rating["field"]}
    if hoisted is not None:
        mark, items = hoisted
        out["mark"] = mark
        out["competencyFeedback"] = items
    out["scales"] = [scale]
    out["outline"] = [
        _upgrade_section(section, scale["id"], rating["field"], hoisted is not None) for section in sections
    ]
    display = raw.get("display")
    if "display" in raw:
        if not isinstance(display, Mapping):
            raise TypeError("display must be an object")
        _upgrade_display(display, levels, out, advanced)
    if _uses_legacy_units(rating, display):
        advanced["legacyUnits"] = True
    extra = {key: value for key, value in raw.items() if key not in _TOP_LEVEL_KEYS}
    if extra:
        advanced["extra"] = extra
    if advanced:
        out["advanced"] = advanced
    if "basedOn" in raw:
        out["basedOn"] = raw["basedOn"]
    return out


def _scale_from_rating(rating: Mapping[str, Any], advanced: dict[str, Any]) -> dict[str, Any]:
    """The rating as a scale; a RAG rating with no scale of its own is remembered as implicit."""
    kind = rating.get("kind")
    if kind == "range":
        low, high = rating["minimum"], rating["maximum"]
        return {
            "id": "marks",
            "name": f"{_whole_if_integral(low)} to {_whole_if_integral(high)}",
            "from": low,
            "to": high,
            "step": _STEP_FROM_V2[rating["step"]],
        }
    if kind == "boolean":
        return {
            "id": "competent",
            "name": "Competent / Not competent",
            "levels": copy.deepcopy(BOOLEAN_LEVELS),
        }
    if kind == "rag":
        if "scale" not in rating:
            advanced["ragScaleImplicit"] = True
        values = list(rating.get("scale") or validation.RAG_SCALE)
        labels = {"G": "Green", "A": "Amber", "R": "Red"}
        scale_id, name = "rag", "RAG"
    elif kind == "scale":
        values = list(rating["scale"])
        labels = {value: value for value in values}
        scale_id, name = "scale", "Scale"
    else:
        raise ValueError("unknown rating kind")
    count = len(values)
    points = rating.get("points")
    levels = [
        {
            "value": value,
            "label": labels.get(value, value),
            "points": points[index] if points is not None else count - index,
        }
        for index, value in enumerate(values)
    ]
    return {"id": scale_id, "name": name, "levels": levels}


def _map(value: Any) -> Mapping[str, Any]:
    """The value when it is an object, else an empty one."""
    return value if isinstance(value, Mapping) else {}


def _whole_if_integral(value: Any) -> Any:
    """A whole number without its decimal point, for a scale's name."""
    return int(value) if isinstance(value, float) and value.is_integer() else value


def _uses_legacy_units(rating: Mapping[str, Any], display: Any) -> bool:
    """Whether an old labelled scale sums fractions, which a scheme keeps by leaving points off."""
    if rating.get("kind") not in ("rag", "scale") or "points" in rating or not isinstance(display, Mapping):
        return False
    aggregates = [
        (display.get(part) or {}).get("aggregate") if isinstance(display.get(part), Mapping) else None
        for part in ("domain", "total")
    ]
    return any(aggregate in ("sum", "mean") for aggregate in aggregates)


def _hoisted_fields(
    sections: Sequence[Any], rating: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]] | None:
    """The mark and feedback every domain shares, when every domain answers the same fields."""
    domains = [entry for entry in sections if isinstance(entry, Mapping) and entry.get("kind") == "domain"]
    if not domains or any("competencyFields" not in entry for entry in domains):
        return None
    first = domains[0]["competencyFields"]
    if any(entry["competencyFields"] != first for entry in domains):
        return None
    mark, items = _split_fields(first, rating["field"])
    return None if mark is None else (mark, items)


def _split_fields(fields: Any, rating_field: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """A competency's fields as its mark (the rating field) and the feedback items beside it."""
    if not isinstance(fields, list):
        raise TypeError("fields must be a list")
    mark: dict[str, Any] | None = None
    items: list[dict[str, Any]] = []
    for index, spec in enumerate(fields):
        if (
            mark is None
            and isinstance(spec, Mapping)
            and spec.get("type") == "rating"
            and spec.get("id") == rating_field
        ):
            mark = {
                "field": spec["id"],
                **{key: value for key, value in spec.items() if key not in ("id", "type")},
            }
            if index != 0:
                mark["at"] = index
            continue
        items.append(_item(spec))
    return mark, items


def _item(spec: Any) -> dict[str, Any]:
    """One written field as a feedback item, or as a custom item when the blocks cannot say it."""
    if not _is_mappable(spec):
        return {"id": spec.get("id") if isinstance(spec, Mapping) else None, "custom": spec}
    item: dict[str, Any] = {
        "id": spec["id"],
        "kind": _ROLE_TO_KIND[spec["role"]],
        "shape": _TYPE_TO_SHAPE[spec["type"]],
    }
    for key in _ITEM_KEYS:
        if key in spec:
            item[key] = spec[key]
    extra = {key: spec[key] for key in _ITEM_EXTRA_KEYS if key in spec}
    if extra:
        item["advanced"] = extra
    return item


def _is_mappable(spec: Any) -> bool:
    """Whether a field is exactly something an item can say and compile back."""
    if not isinstance(spec, Mapping) or not isinstance(spec.get("id"), str):
        return False
    allowed = {"id", "type", "role", *_ITEM_KEYS, *_ITEM_EXTRA_KEYS}
    return (
        spec.get("type") in _TYPE_TO_SHAPE
        and spec.get("role") in _ROLE_TO_KIND
        and "fields" not in spec
        and "options" not in spec
        and spec.get("source", "marker") == "marker"
        and set(spec) <= allowed
    )


def _upgrade_section(section: Any, scale_id: str, rating_field: str, hoisted: bool) -> dict[str, Any]:
    """One v2 section as an outline block."""
    if not isinstance(section, Mapping):
        return {"block": "custom", "raw": section}
    kind = section.get("kind")
    if kind == "domain":
        return _upgrade_domain(section, scale_id, rating_field, hoisted)
    if kind == "section":
        block: dict[str, Any] = {"block": "notes"}
        for key in ("id", "title", "instructions"):
            if key in section:
                block[key] = section[key]
        if "fields" in section:
            block["feedback"] = [_item(spec) for spec in _list(section["fields"])]
        other = {key: value for key, value in section.items() if key not in _SECTION_KEYS}
        if other:
            block["advanced"] = other
        return block
    if kind == "field" and isinstance(section.get("field"), Mapping) and "id" in section["field"]:
        block = {
            "block": "notes",
            "id": section["field"]["id"],
            "single": True,
            "feedback": [_item(section["field"])],
        }
        other = {key: value for key, value in section.items() if key not in ("kind", "field")}
        if other:
            block["advanced"] = other
        return block
    return {"block": "custom", "raw": section}


def _upgrade_domain(
    section: Mapping[str, Any], scale_id: str, rating_field: str, hoisted: bool
) -> dict[str, Any]:
    """A v2 domain as a domain block."""
    block: dict[str, Any] = {"block": "domain"}
    for key in ("id", "title", "instructions", "live", "description"):
        if key in section:
            block[key] = section[key]
    if "nullable" in section:
        block["optional"] = section["nullable"]
    block["scale"] = scale_id
    if "competencies" in section:
        block["competencies"] = section["competencies"]
    if "competencyFields" in section and not hoisted:
        mark, items = _split_fields(section["competencyFields"], rating_field)
        if mark is not None:
            block["mark"] = mark
        block["competencyFeedback"] = items
    if "fields" in section:
        block["feedback"] = [_item(spec) for spec in _list(section["fields"])]
    other = {key: value for key, value in section.items() if key not in _DOMAIN_KEYS}
    if other:
        block["advanced"] = other
    return block


def _list(value: Any) -> list[Any]:
    """A list, refusing anything else so the upgrade falls back to keeping the structure raw."""
    if not isinstance(value, list):
        raise TypeError("expected a list")
    return value


def _upgrade_display(
    display: Mapping[str, Any],
    levels: Sequence[Mapping[str, Any]],
    out: dict[str, Any],
    advanced: dict[str, Any],
) -> None:
    """The v2 display as pass rules, show switches, tone and the leftovers kept under advanced."""
    pass_: dict[str, Any] = {}
    for part, target, aggregate_key in (("domain", "domain", "ragCounts"), ("total", "overall", "ragShare")):
        if part not in display:
            continue
        node = display[part]
        if not isinstance(node, Mapping):
            raise TypeError("display parts must be objects")
        rule_holder: dict[str, Any] = {}
        if "aggregate" in node:
            rule_holder["score"] = _AGGREGATE_TO_SCORE[node["aggregate"]]
        if node.get("passAtLeast") is not None:
            if node.get("aggregate") == aggregate_key and levels:
                rule_holder["rule"] = {
                    "type": "labels",
                    "atLeast": node["passAtLeast"],
                    "of": "percent",
                    "value": levels[0]["value"],
                }
            else:
                rule_holder["rule"] = {"type": "score", "atLeast": node["passAtLeast"]}
        elif "rule" in node:
            rule_holder["rule"] = node["rule"]
        if "requireEveryDomain" in node:
            rule_holder["everyDomainPasses"] = node["requireEveryDomain"]
        if "max" in node:
            advanced["outOf"] = node["max"]
        pass_[target] = rule_holder
    if pass_:
        out["pass"] = pass_
    for key in ("tones", "bands", "labels"):
        if key in display:
            advanced[key] = display[key]
    if "show" in display:
        out["show"] = {
            validation.SHOW_FROM_V2.get(key, key): value for key, value in dict(display["show"]).items()
        }
    if "feedbackTone" in display:
        out["tone"] = display["feedbackTone"]


# --- The author's scheme -> version 2 ---------------------------------------------------


def compile_v3(raw: Mapping[str, Any]) -> dict[str, Any]:
    """The version 2 form of a scheme, which every reader marks against; never raises."""
    scheme = copy.deepcopy(dict(raw)) if isinstance(raw, Mapping) else {}
    advanced = _map(scheme.get("advanced"))
    kept = advanced.get("raw")
    if isinstance(kept, Mapping):
        out = dict(kept)
        if "basedOn" in scheme:
            out["basedOn"] = scheme["basedOn"]
        return out
    out = {"schemaVersion": validation.SCHEMA_VERSION}
    for key in ("instructions", "basedOn"):
        if key in scheme:
            out[key] = scheme[key]
    scale = _chosen_scale(scheme)
    mark = _map(scheme.get("mark"))
    if scale is not None:
        out["rating"] = _compile_rating(scale, str(mark.get("field", "score")), scheme, advanced)
    outline = scheme.get("outline")
    out["sections"] = (
        [_compile_block(block, scheme) for block in outline] if isinstance(outline, list) else []
    )
    display = _compile_display(scheme, scale, advanced)
    if display:
        out["display"] = display
    extra = advanced.get("extra")
    if isinstance(extra, Mapping):
        out.update(extra)
    return out


def _chosen_scale(scheme: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """The scale the first domain uses, else the first scale."""
    scales = [scale for scale in scheme.get("scales") or [] if isinstance(scale, Mapping)]
    outline = scheme.get("outline")
    first_domain = next(
        (block for block in outline or [] if isinstance(block, Mapping) and block.get("block") == "domain"),
        None,
    )
    wanted = first_domain.get("scale") if first_domain else None
    return next((scale for scale in scales if scale.get("id") == wanted), scales[0] if scales else None)


def _is_boolean(values: Sequence[Any]) -> bool:
    """Whether levels are exactly yes then no (not 1 then 0, which Python also calls equal)."""
    return len(values) == 2 and values[0] is True and values[1] is False


def _compile_rating(
    scale: Mapping[str, Any], field: str, scheme: Mapping[str, Any], advanced: Mapping[str, Any]
) -> dict[str, Any]:
    """The v2 rating for a scale: its kind is decided by the shape of its levels."""
    if "from" in scale:
        return {
            "kind": "range",
            "minimum": scale["from"],
            "maximum": scale.get("to"),
            "step": _STEP_TO_V2.get(str(scale.get("step", "any")), "number"),
            "field": field,
        }
    levels = [level for level in scale.get("levels") or [] if isinstance(level, Mapping)]
    values = [level.get("value") for level in levels]
    if _is_boolean(values):
        return {"kind": "boolean", "field": field}
    is_rag = values == list(validation.RAG_SCALE)
    rating: dict[str, Any] = {"kind": "rag" if is_rag else "scale", "field": field}
    if not (is_rag and advanced.get("ragScaleImplicit")):
        rating["scale"] = [str(value) for value in values]
    points = level_points(levels)
    pass_ = _map(scheme.get("pass"))
    sums = any(
        isinstance(pass_.get(part), Mapping) and pass_[part].get("score") in ("sum", "mean")
        for part in ("domain", "overall")
    )
    if not points_are_positions(points) or (sums and not advanced.get("legacyUnits")):
        rating["points"] = points
    return rating


def level_points(levels: Sequence[Mapping[str, Any]]) -> list[float]:
    """The points of each level, best first, as numbers."""
    return [level.get("points", 0) for level in levels]


def points_are_positions(points: Sequence[float]) -> bool:
    """Whether points are n..1, which compile leaves implicit."""
    return list(points) == [len(points) - index for index in range(len(points))]


def _compile_block(block: Any, scheme: Mapping[str, Any]) -> Any:
    """One outline block as a v2 section."""
    if not isinstance(block, Mapping):
        return block
    kind = block.get("block")
    if kind == "domain":
        return _compile_domain(block, scheme)
    if kind == "notes":
        advanced = _map(block.get("advanced"))
        feedback = [_compile_item(item) for item in block.get("feedback") or []]
        if block.get("single"):
            return {"kind": "field", "field": feedback[0] if feedback else {}, **advanced}
        out: dict[str, Any] = {"kind": "section"}
        for key in ("id", "title", "instructions"):
            if key in block:
                out[key] = block[key]
        if "feedback" in block:
            out["fields"] = feedback
        out.update(advanced)
        return out
    return block.get("raw") if kind == "custom" else dict(block)


def _compile_domain(block: Mapping[str, Any], scheme: Mapping[str, Any]) -> dict[str, Any]:
    """A domain block as a v2 domain."""
    out: dict[str, Any] = {"kind": "domain"}
    for key in ("id", "title", "instructions", "live", "description"):
        if key in block:
            out[key] = block[key]
    if "optional" in block:
        out["nullable"] = block["optional"]
    if "competencies" in block:
        out["competencies"] = block["competencies"]
    if "mark" in block or "competencyFeedback" in block:
        out["competencyFields"] = _compile_fields(block.get("mark"), block.get("competencyFeedback"))
    elif "competencyFeedback" in scheme:
        out["competencyFields"] = _compile_fields(scheme.get("mark"), scheme["competencyFeedback"])
    if "feedback" in block:
        out["fields"] = [_compile_item(item) for item in block["feedback"] or []]
    if isinstance(block.get("advanced"), Mapping):
        out.update(block["advanced"])
    return out


def _compile_fields(mark: Any, items: Any) -> list[Any]:
    """What every competency answers: the feedback items with the rating field put back."""
    fields = [_compile_item(item) for item in items or []]
    if isinstance(mark, Mapping) and "field" in mark:
        rating_field = {
            "id": mark["field"],
            "type": "rating",
            **{key: value for key, value in mark.items() if key not in ("field", "at")},
        }
        at = mark.get("at", 0)
        fields.insert(at if isinstance(at, int) else 0, rating_field)
    return fields


def _compile_item(item: Any) -> Any:
    """One feedback item as a v2 field."""
    if not isinstance(item, Mapping):
        return item
    if "custom" in item:
        return item["custom"]
    out: dict[str, Any] = {
        "id": item.get("id"),
        "type": _SHAPE_TO_TYPE.get(str(item.get("shape")), "longText"),
        "role": _KIND_TO_ROLE.get(str(item.get("kind")), "other"),
    }
    for key in _ITEM_KEYS:
        if key in item:
            out[key] = item[key]
    if isinstance(item.get("advanced"), Mapping):
        out.update(item["advanced"])
    return out


def _compile_display(
    scheme: Mapping[str, Any], scale: Mapping[str, Any] | None, advanced: Mapping[str, Any]
) -> dict[str, Any]:
    """The v2 display: pass rules, tones, bands, labels, show switches and tone."""
    display: dict[str, Any] = {}
    levels = [level for level in (scale or {}).get("levels") or [] if isinstance(level, Mapping)]
    best = levels[0].get("value") if levels else None
    top_points = level_points(levels)[:2]
    best_is_alone = len(top_points) < 2 or top_points[0] > top_points[1]
    pass_ = _map(scheme.get("pass"))
    for part, target, table in (
        ("domain", "domain", validation.DOMAIN_SCORE_AGGREGATES),
        ("overall", "total", validation.TOTAL_SCORE_AGGREGATES),
    ):
        node = pass_.get(part)
        outof = advanced.get("outOf") if part == "overall" else None
        if not isinstance(node, Mapping) and outof is None:
            continue
        compiled: dict[str, Any] = {}
        node = _map(node)
        score = node.get("score")
        if score in table:
            compiled["aggregate"] = table[score]
        rule = node.get("rule")
        if isinstance(rule, Mapping):
            if rule.get("type") == "score" or (
                score == "labels"
                and rule.get("type") == "labels"
                and rule.get("of") == "percent"
                and best_is_alone
                and rule.get("value") == best
                and type(rule.get("value")) is type(best)
            ):
                compiled["passAtLeast"] = rule.get("atLeast")
            else:
                compiled["rule"] = rule
        if "everyDomainPasses" in node:
            compiled["requireEveryDomain"] = node["everyDomainPasses"]
        if outof is not None:
            compiled["max"] = outof
        display[target] = compiled
    for key in ("tones", "bands", "labels"):
        if key in advanced:
            display[key] = advanced[key]
    if isinstance(scheme.get("show"), Mapping):
        display["show"] = {
            validation.SHOW_TO_V2.get(key, key): value for key, value in scheme["show"].items()
        }
    if scheme.get("tone") is not None:
        display["feedbackTone"] = scheme["tone"]
    return display


# --- Problems, at the author's own paths -------------------------------------------------

_SECTION_PATH = re.compile(r"^sections\[(\d+)\](\.competencies\[(\d+)\])?")


def scheme_path(v2_path: str) -> str:
    """Where a problem found in the compiled form sits in the author's scheme."""
    found = _SECTION_PATH.match(v2_path)
    if found:
        block = f"outline[{found.group(1)}]"
        return f"{block}.competencies[{found.group(3)}]" if found.group(2) else block
    if v2_path.startswith("rating"):
        return "scales"
    if v2_path.startswith("display.domain"):
        return "pass.domain"
    if v2_path.startswith("display.total"):
        return "pass.overall"
    if v2_path.startswith("display"):
        return "pass"
    return ""


def validate_scheme(raw: Any, compiled: Mapping[str, Any] | None = None) -> list[validation.ValidationError]:
    """Every problem with a scheme, at its v3 path; empty when it can be published.

    Pass `compiled` (the scheme's `compile_v3`) when the caller already has it, to compile once.
    """
    if not isinstance(raw, Mapping):
        return [{"path": "", "message": _NOT_A_SCHEME}]
    advanced = _map(raw.get("advanced"))
    if advanced.get("raw") is not None:
        return [
            {
                "path": f"advanced.raw.{problem['path']}" if problem["path"] else "advanced.raw",
                "message": problem["message"],
            }
            for problem in validation.validate_structure(
                compiled if compiled is not None else compile_v3(raw)
            )
        ]
    checker = _SchemeChecker(raw)
    checker.run()
    if checker.errors:
        return checker.errors
    return [
        {"path": scheme_path(problem["path"]), "message": problem["message"]}
        for problem in validation.validate_structure(compiled if compiled is not None else compile_v3(raw))
    ]


_ID_OK = validation.IDENTIFIER_PATTERN
_ID_MESSAGE = validation.IDENTIFIER_MESSAGE
_DIFFERENT_SCALES = "Every Domain must use the same rating scale for now. Choose one scale for all of them."
_NO_SUCH_LEVEL = (
    "The pass mark uses a level that is not on the rating scale. "
    "Choose one of its levels, such as Good or Fair."
)


class _SchemeChecker:
    """One pass over a scheme, collecting every problem at its v3 path."""

    def __init__(self, raw: Mapping[str, Any]) -> None:
        """Hold the scheme and its scales by id."""
        self.raw = raw
        self.errors: list[validation.ValidationError] = []
        scales = raw.get("scales")
        self.scales: list[Any] = scales if isinstance(scales, list) else []
        self.by_id = {
            scale["id"]: scale
            for scale in self.scales
            if isinstance(scale, Mapping) and isinstance(scale.get("id"), str)
        }

    def fail(self, path: str, message: str) -> None:
        """Record one problem."""
        self.errors.append({"path": path, "message": message})

    def run(self) -> None:
        """Every check, in the order an author reads the scheme."""
        self.check_scales()
        self.check_outline()
        self.check_feedback_list(self.raw.get("competencyFeedback"), "competencyFeedback")
        self.check_pass()
        self.check_show_and_tone()

    # scales
    def check_scales(self) -> None:
        """Each scale: an id, and levels best first or a number range."""
        if not self.scales:
            self.fail(
                "scales",
                "Add a rating scale so markers know how to rate each Competency, for example Good, Fair "
                "and Poor.",
            )
        seen: set[str] = set()
        for index, scale in enumerate(self.scales):
            path = f"scales[{index}]"
            if not isinstance(scale, Mapping):
                self.fail(path, "This rating scale is not set up correctly. Remove it and add it again.")
                continue
            scale_id = scale.get("id")
            if not isinstance(scale_id, str) or not _ID_OK.match(scale_id):
                self.fail(f"{path}.id", _ID_MESSAGE)
            elif scale_id in seen:
                self.fail(f"{path}.id", "Two rating scales have the same name. Give each its own name.")
            else:
                seen.add(scale_id)
            if "levels" in scale:
                self.check_levels(scale, path)
            elif "from" in scale or "to" in scale:
                low, high = scale.get("from"), scale.get("to")
                if not validation.is_number(low) or not validation.is_number(high) or low >= high:
                    self.fail(
                        path,
                        "A number scale needs a lowest number that is smaller than the highest, for "
                        "example 1 to 5.",
                    )
                if scale.get("step", "any") not in validation.SCALE_STEPS:
                    self.fail(
                        f"{path}.step",
                        "Choose whether markers give whole numbers only or any number, including decimals.",
                    )
            else:
                self.fail(
                    path,
                    "A rating scale needs either named levels, such as Good, Fair and Poor, or a lowest "
                    "and highest number, such as 1 to 5.",
                )

    def check_levels(self, scale: Mapping[str, Any], path: str) -> None:
        """A scale's levels: distinct words (or yes and no), points that never rise."""
        levels = scale["levels"] if isinstance(scale["levels"], list) else []
        values = [level.get("value") for level in levels if isinstance(level, Mapping)]
        yes_no = _is_boolean(values)
        seen: list[Any] = []
        previous: Any = None
        for index, level in enumerate(levels):
            level_path = f"{path}.levels[{index}]"
            if not isinstance(level, Mapping):
                self.fail(level_path, "This level is not set up correctly. Remove it and add it again.")
                continue
            value = level.get("value")
            if not isinstance(value, str) and not (yes_no and isinstance(value, bool)):
                self.fail(
                    f"{level_path}.value",
                    "Each level needs a name, such as Good or Fair, or must be a Yes or No choice.",
                )
            elif any(
                value is earlier or (type(value) is type(earlier) and value == earlier) for earlier in seen
            ):
                self.fail(
                    f"{level_path}.value", "Two levels have the same name. Give each level its own name."
                )
            seen.append(value)
            points = level.get("points")
            if not validation.is_number(points) or points < 0:
                self.fail(f"{level_path}.points", "Points must be a number, 0 or more.")
            else:
                if previous is not None and points > previous:
                    self.fail(
                        f"{level_path}.points",
                        "A lower level cannot earn more points than the one above it. List the best level "
                        "first, for example Good, then Fair, then Poor.",
                    )
                previous = points
        if yes_no and level_points([level for level in levels if isinstance(level, Mapping)]) != [1, 0]:
            self.fail(path, "A Yes or No scale must give 1 point for Yes and 0 points for No.")

    # outline
    def check_outline(self) -> None:
        """Blocks: domains with competencies, notes with feedback, custom ones left alone."""
        outline = self.raw.get("outline")
        if not isinstance(outline, list) or not outline:
            self.fail("outline", "Add at least one Domain, otherwise the marker has nothing to mark.")
            return
        seen: set[str] = set()
        first_scale: Any = None
        mixed_reported = False
        default_scale = (
            self.scales[0].get("id") if self.scales and isinstance(self.scales[0], Mapping) else None
        )
        for index, block in enumerate(outline):
            path = f"outline[{index}]"
            if not isinstance(block, Mapping) or block.get("block") not in validation.BLOCK_KINDS:
                self.fail(
                    f"{path}.block",
                    "Each part of the marking scheme must be a Domain, a notes section or a custom section.",
                )
                continue
            if block["block"] == "custom":
                continue
            block_id = block.get("id")
            if not isinstance(block_id, str) or not _ID_OK.match(block_id):
                self.fail(f"{path}.id", _ID_MESSAGE)
            elif block_id in seen:
                self.fail(
                    f"{path}.id",
                    "Two parts of the marking scheme have the same name. Give each its own name.",
                )
            else:
                seen.add(block_id)
            if block["block"] == "notes":
                self.check_feedback_list(block.get("feedback"), f"{path}.feedback")
                continue
            scale_ref = block.get("scale", default_scale)
            if scale_ref not in self.by_id:
                self.fail(
                    f"{path}.scale",
                    "This Domain uses a rating scale that is not in the marking scheme. Choose one of the "
                    "scales you have added.",
                )
            elif first_scale is None:
                first_scale = scale_ref
            elif scale_ref != first_scale and not mixed_reported:
                self.fail(f"{path}.scale", _DIFFERENT_SCALES)
                mixed_reported = True
            self.check_competencies(block, path, self.by_id.get(scale_ref))
            self.check_feedback_list(block.get("feedback"), f"{path}.feedback")
            self.check_feedback_list(block.get("competencyFeedback"), f"{path}.competencyFeedback")

    def check_competencies(
        self, block: Mapping[str, Any], path: str, scale: Mapping[str, Any] | None
    ) -> None:
        """A domain's competencies: at least one, distinct ids, descriptors on real levels."""
        competencies = block.get("competencies")
        if not isinstance(competencies, list) or not competencies:
            self.fail(f"{path}.competencies", "Add at least one Competency to this Domain.")
            return
        words = (
            [level.get("value") for level in scale["levels"] if isinstance(level, Mapping)]
            if scale and isinstance(scale.get("levels"), list)
            else None
        )
        seen: set[str] = set()
        for index, competency in enumerate(competencies):
            where = f"{path}.competencies[{index}]"
            if not isinstance(competency, Mapping):
                self.fail(where, "This Competency is not set up correctly. Remove it and add it again.")
                continue
            competency_id = competency.get("id")
            if not isinstance(competency_id, str) or not _ID_OK.match(competency_id):
                self.fail(f"{where}.id", _ID_MESSAGE)
            elif competency_id in seen:
                self.fail(
                    f"{where}.id",
                    "Two Competencies in this Domain have the same name. Give each its own name.",
                )
            else:
                seen.add(competency_id)
            descriptors = competency.get("descriptors")
            if (
                words is not None
                and all(isinstance(word, str) for word in words)
                and isinstance(descriptors, Mapping)
            ):
                for key in descriptors:
                    if key not in words:
                        self.fail(
                            f"{where}.descriptors",
                            f'The description for "{key}" does not match any level on the rating scale. '
                            "Use a level from the scale, or remove it.",
                        )

    def check_feedback_list(self, items: Any, path: str) -> None:
        """Feedback items: an id, what it is and how it is written (custom ones are skipped)."""
        if not isinstance(items, list):
            return
        for index, item in enumerate(items):
            where = f"{path}[{index}]"
            if not isinstance(item, Mapping) or "custom" in item:
                continue
            item_id = item.get("id")
            if not isinstance(item_id, str) or not _ID_OK.match(item_id):
                self.fail(f"{where}.id", _ID_MESSAGE)
            if item.get("kind") not in validation.FEEDBACK_KINDS:
                self.fail(
                    f"{where}.kind",
                    "Choose what kind of feedback this is.",
                )
            if item.get("shape") not in validation.FEEDBACK_SHAPES:
                self.fail(
                    f"{where}.shape",
                    "Choose how this feedback is written: a single line, a paragraph or a list.",
                )

    # pass, show, tone
    def check_pass(self) -> None:
        """How a domain and the whole are scored, and the line they pass at."""
        pass_ = self.raw.get("pass")
        if not isinstance(pass_, Mapping):
            return
        scale = _chosen_scale(self.raw)
        has_levels = bool(scale and isinstance(scale.get("levels"), list))
        levels = (
            [level.get("value") for level in scale["levels"] if isinstance(level, Mapping)]
            if has_levels and scale
            else []
        )
        for which in ("domain", "overall"):
            node = pass_.get(which)
            path = f"pass.{which}"
            if not isinstance(node, Mapping):
                continue
            score = node.get("score")
            if "score" in node and score not in validation.SCORE_KINDS:
                self.fail(
                    f"{path}.score",
                    "Choose how a score is worked out: count the ratings, add them up, take the average or "
                    "use a percentage.",
                )
            elif score == "labels" and not has_levels:
                self.fail(
                    f"{path}.score",
                    "Counting how many ratings reach a level only works when ratings are named levels, "
                    "such as Good or Fair. Your scale uses numbers, so choose Add up or Average instead.",
                )
            self.check_rule(node.get("rule"), score, f"{path}.rule", scale, levels)
        overall = pass_.get("overall")
        domain = pass_.get("domain")
        if (
            isinstance(overall, Mapping)
            and overall.get("everyDomainPasses")
            and not (isinstance(domain, Mapping) and domain.get("rule"))
        ):
            self.fail(
                "pass.overall.everyDomainPasses",
                "To require every Domain to pass, set a pass mark for each Domain first.",
            )

    def check_rule(
        self, rule: Any, score: Any, path: str, scale: Mapping[str, Any] | None, levels: list[Any]
    ) -> None:
        """One pass rule: a score to reach, or a count of ratings at a level or better."""
        if rule is None:
            return
        if not isinstance(rule, Mapping) or rule.get("type") not in validation.RULE_TYPES:
            self.fail(f"{path}.type", "Choose a pass mark based on either a score or a count of ratings.")
            return
        if score == "labels" and rule["type"] == "score":
            self.fail(
                f"{path}.type",
                "When you count ratings, say how many must reach a level, for example at least 3 rated "
                "Fair or better.",
            )
        at_least = rule.get("atLeast")
        if not validation.is_number(at_least) or at_least < 0:
            self.fail(f"{path}.atLeast", "The pass mark must be a number, 0 or more.")
        if rule["type"] != "labels":
            return
        if rule.get("of") not in validation.RULE_OF:
            self.fail(
                f"{path}.of",
                "Choose whether the pass mark is a number of Competencies or a percentage of them.",
            )
        elif rule["of"] == "percent" and validation.is_number(at_least) and at_least > 100:
            self.fail(f"{path}.atLeast", "A percentage cannot be more than 100.")
        value = rule.get("value")
        if levels:
            known = any(value is level or (type(value) is type(level) and value == level) for level in levels)
        else:
            low, high = (scale or {}).get("from"), (scale or {}).get("to")
            known = (
                validation.is_number(value)
                and validation.is_number(low)
                and validation.is_number(high)
                and low <= value <= high
            )
        if not known:
            self.fail(f"{path}.value", _NO_SUCH_LEVEL)

    def check_show_and_tone(self) -> None:
        """What the candidate sees, and the tone the marker writes in."""
        show = self.raw.get("show")
        if isinstance(show, Mapping):
            for key, value in show.items():
                if key not in validation.SCHEME_SHOW:
                    self.fail(
                        f"show.{key}", f'"{key}" is not a part of the feedback that can be shown or hidden.'
                    )
                elif not isinstance(value, bool):
                    self.fail(f"show.{key}", "Choose Shown or Hidden.")
        tone = self.raw.get("tone")
        if tone is not None and tone not in validation.FEEDBACK_TONES:
            self.fail("tone", "Choose a tone for the feedback: supportive, formal or brief.")
