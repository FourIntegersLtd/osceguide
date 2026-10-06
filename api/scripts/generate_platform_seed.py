"""Build `seeds/platform-starter.json` and the exam profiles from the captured legacy models.

Run when the fixtures under `tests/fixtures/` or the hints under
`seeds/rubric_hints/` change; the output is committed, so a deployment seeds
from a file rather than from the test tree.

    PYTHONPATH=. poetry run python scripts/generate_platform_seed.py

One generic converter (`rubric_from_model`): any legacy pydantic JSON schema
in, a version 2 rubric out. Nothing below names an exam or its fields. The walk
reads the model's shape:

- a *competency* is an object holding the rating field its hint names (`score`,
  or CASC's `competent`) as a rating: a boolean, a bounded number, or a string
  restricted to single letters (R/A/G);
- a *domain* is an object whose children include competencies; its other
  children are fields the domain answers once;
- any other object at the top is a written *section*, and any other property a
  lone *field*.

Every description the model read is carried verbatim: a competency's becomes its
instructions (and its anchors, where it spells them out, its descriptors), a
field's its instructions, the root's the rubric's instructions. The same
wording is written to `app/features/rubrics/profiles/<exam>.json`, keyed by the
qualified path, as the draft instructions an author starts from;
`profiles/_generic.json` is the fallback for any rubric, keyed by role.

What is genuinely per exam and not in the legacy model (its name, clock, the
rating field, a role the name cannot tell, and how the dashboard reads it) is
data in `seeds/rubric_hints/<exam>.json`: the only exam-specific files.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.features.rubrics.authoring import profile_of
from app.features.rubrics.domain import parse_structure
from app.features.rubrics.legacy_model import (
    field_from_schema,
    humanise,
    inline,
    ordered_children,
    rating_of,
    unwrap,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "tests/fixtures/legacy_schemas/b2c"
PROMPTS = ROOT / "tests/fixtures/legacy_prompts"
# Marking prompts written for this platform, for exams legacy never had one for.
AUTHORED_PROMPTS = ROOT / "seeds/prompts"
HINTS = ROOT / "seeds/rubric_hints"
OUT = ROOT / "seeds/platform-starter.json"
PROFILES = ROOT / "app/features/rubrics/profiles"
# The seed's exam order, which is the catalogue's order.
EXAM_CODES = ("sca", "plab", "casc", "ortho")

# Storage keys on the legacy models, not anything anyone is marked on. The same
# list b2b's registry stripped. `live_coverage` is written by the live pipeline,
# not the marker; it stays stored metadata until the field vocabulary can
# describe it (plan Stage 1 deviation).
META = {
    "attempt_id",
    "created_at",
    "evaluated_by",
    "feedback_id",
    "liked_by",
    "likes",
    "live_coverage",
    "mock_id",
    "station_id",
    "updated_at",
    "user_id",
}

# The draft instruction for a part no exam profile covers, by role, or by
# `domain`, `competency` or `section` for those parts.
GENERIC_PROFILE: dict[str, str] = {
    "domain": "What this domain assesses, and what the marker should look for across its competencies.",
    "competency": "What the candidate must do to meet this competency, and what falls short.",
    "section": "What this section asks the marker to write.",
    "rating": "The rating for this competency, on the rubric's own scale.",
    "evidence": "A short quote or paraphrase from the transcript that supports the rating.",
    "explanation": "Why this rating was given, referring to what the candidate did or missed.",
    "strength": "What the candidate did well.",
    "improvement": "What the candidate missed or should do differently.",
    "action": "A concrete next step the candidate can practise.",
    "flag": "A safety or critical issue, if there was one.",
    "summary": "A short overall summary.",
    "selector": "Which variant of the station this was.",
    "other": "",
}


def split_description(text: str, values: list[str]) -> dict[str, str]:
    """The anchors a legacy competency description spells out, by rating value.

    An anchor runs from its "G:" line until a header ("Key aspects:"), a
    bullet or the next value.
    """
    anchor_line = re.compile(rf"^({'|'.join(map(re.escape, values))}):\s*(.*)$") if values else None
    descriptors: dict[str, str] = {}
    current: str | None = None
    for line in (raw_line.strip() for raw_line in text.splitlines()):
        if not line:
            continue
        anchor = anchor_line.match(line) if anchor_line else None
        if anchor:
            current = anchor[1]
            descriptors[current] = anchor[2]
            continue
        if current and not line.endswith(":") and not line.startswith("-"):
            descriptors[current] = f"{descriptors[current]} {line}"
            continue
        current = None
    return descriptors


def rubric_from_model(schema: Mapping[str, Any], hints: Mapping[str, Any]) -> dict[str, Any]:
    """One legacy model's JSON schema as a version 2 rubric structure.

    `hints` supplies only what the schema cannot: the rating field, roles a
    field's name does not tell, the platform-written fields, the domains marked
    live during the consultation, and the display.
    Refuses (SystemExit) a model whose competencies disagree on the rating or
    on what they answer, rather than guessing.
    """
    model = inline(schema, schema.get("$defs", {}))
    rating_field = str(hints["ratingField"])
    roles: dict[str, str] = dict(hints.get("roles") or {})
    system_fields = frozenset(hints.get("systemFields") or ())
    live_domains = frozenset(hints.get("liveDomains") or ())
    top_level = [
        (name, node, required) for name, node, required in ordered_children(model) if name not in META
    ]

    def competency_rating(node: Mapping[str, Any]) -> dict[str, Any] | None:
        """The rating a competency object holds in the rating field, or None if it is not one."""
        inner, nullable = unwrap(node)
        if nullable or inner.get("type") != "object":
            return None
        rating_node = (inner.get("properties") or {}).get(rating_field)
        return rating_of(unwrap(rating_node)[0]) if isinstance(rating_node, Mapping) else None

    ratings = [
        rating
        for _, node, _ in top_level
        for _, child, _ in ordered_children(unwrap(node)[0])
        if (rating := competency_rating(child)) is not None
    ]
    if not ratings or any(rating != ratings[0] for rating in ratings):
        raise SystemExit(f"competencies must all rate {rating_field!r} the same way; found {ratings}")
    rating = {**ratings[0], "field": rating_field}
    scale = list(rating.get("scale") or [])

    def field(field_id: str, node: Mapping[str, Any], required: bool) -> dict[str, Any]:
        """One property as a rubric field, with this rubric's rating field, roles and system fields."""
        return field_from_schema(
            field_id,
            node,
            required=required,
            rating_field=rating_field,
            roles=roles,
            system_fields=system_fields,
        )

    sections: list[dict[str, Any]] = []
    for name, node, required in top_level:
        inner, nullable = unwrap(node)
        children = ordered_children(inner) if inner.get("type") == "object" else []
        if not children:
            sections.append({"kind": "field", "field": field(name, node, required)})
            continue
        section: dict[str, Any] = {"id": name, "title": humanise(name)}
        if nullable:
            # pydantic's `X | None = None`: the object's own description is the
            # instructions, the wrapper's says what the part is.
            section.update(instructions=inner.get("description", ""), nullable=True)
            if node.get("description"):
                section["description"] = node["description"]
        elif node.get("description"):
            section["instructions"] = node["description"]
        if not required:
            section["required"] = False
        competencies = [(child_id, child) for child_id, child, _ in children if competency_rating(child)]
        if not competencies:
            section["kind"] = "section"
            section["fields"] = [
                field(child_id, child, is_required) for child_id, child, is_required in children
            ]
            sections.append(section)
            continue
        answers = [ordered_children(unwrap(child)[0]) for _, child in competencies]
        if any(answer != answers[0] for answer in answers):
            raise SystemExit(f"{name}: its competencies answer different fields")
        competency_ids = {child_id for child_id, _ in competencies}
        section.update(
            kind="domain",
            # Legacy marked everything after the consultation, so a domain is
            # live only where the exam's hints decide it (`liveDomains`).
            live=section["id"] in live_domains,
            competencies=[
                {
                    "id": child_id,
                    "label": humanise(child_id),
                    "instructions": child.get("description", ""),
                    "descriptors": split_description(child.get("description", ""), scale),
                }
                for child_id, child in competencies
            ],
            competencyFields=[
                field(answer_id, answer, is_required) for answer_id, answer, is_required in answers[0]
            ],
            fields=[
                field(child_id, child, is_required)
                for child_id, child, is_required in children
                if child_id not in competency_ids
            ],
        )
        sections.append(section)

    structure: dict[str, Any] = {"schemaVersion": 2}
    if model.get("description"):
        structure["instructions"] = model["description"]
    structure["rating"] = rating
    structure["sections"] = sections
    structure["display"] = dict(hints["display"])
    return structure


def build() -> tuple[dict[str, Any], dict[str, dict[str, str]]]:
    """The seed file and every exam's profile. Each structure is parsed, so an invalid one never lands."""
    out: dict[str, Any] = {
        "_comment": (
            "Generated by scripts/generate_platform_seed.py from the legacy feedback "
            "schemas and marking prompts captured in api/tests/fixtures/ and "
            "the hints in seeds/rubric_hints/. Do not hand-edit: regenerate. Ids and "
            "wording are the legacy ones, so a migrated result stays comparable with "
            "one marked next week."
        ),
        "exams": [],
    }
    profiles: dict[str, dict[str, str]] = {}
    for code in EXAM_CODES:
        hints = json.loads((HINTS / f"{code}.json").read_text())
        structure = rubric_from_model(json.loads((SCHEMAS / f"{code}.json").read_text()), hints)
        parse_structure(structure)
        profiles[code] = profile_of(structure)
        # An authored prompt wins over the captured legacy one. No fallback: an
        # exam with no prompt of its own is refused here rather than marked with
        # another exam's (CASC was marked with the RCGP GP prompt for years).
        authored_prompt = AUTHORED_PROMPTS / f"{code}_system.txt"
        source = authored_prompt if authored_prompt.exists() else PROMPTS / f"b2c_{code}_system.txt"
        out["exams"].append(
            {
                "code": code,
                "name": hints["name"],
                "default_reading_seconds": hints["readingSeconds"],
                "default_simulation_seconds": hints["simulationSeconds"],
                "station_attempt_limit": 3,
                "rubric": {
                    "title": f"{hints['name']} marking rubric",
                    "structure": structure,
                    "system_prompt": source.read_text(),
                    "pacing": dict(hints["pacing"]),
                    "prompt_source": source.name,
                },
            }
        )
    return out, profiles


def main() -> int:
    """Write the seed and the profiles, and say what each exam came to."""
    data, profiles = build()
    OUT.write_text(json.dumps(data, indent=2) + "\n")
    PROFILES.mkdir(exist_ok=True)
    for code, profile in profiles.items():
        (PROFILES / f"{code}.json").write_text(json.dumps(profile, indent=2) + "\n")
    (PROFILES / "_generic.json").write_text(json.dumps(GENERIC_PROFILE, indent=2) + "\n")
    for exam in data["exams"]:
        sections = exam["rubric"]["structure"]["sections"]
        domains = [section for section in sections if section["kind"] == "domain"]
        competencies = sum(len(domain["competencies"]) for domain in domains)
        print(  # noqa: T201
            f"{exam['code']:6} {exam['rubric']['structure']['rating']['kind']:8} "
            f"{len(domains)} domains, {competencies} competencies, "
            f"{len(sections) - len(domains)} other parts, "
            f"{len(profiles[exam['code']])} profile entries, prompt {exam['rubric']['prompt_source']}"
        )
    print(f"wrote {OUT.relative_to(ROOT)} and {PROFILES.relative_to(ROOT)}/")  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
