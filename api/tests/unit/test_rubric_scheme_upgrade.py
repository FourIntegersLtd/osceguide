"""The author's marking scheme (schemaVersion 3): upgraded from the seeds, compiled back to what marks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.features.rubrics import authoring, domain, schema_builder, scheme

_SEED = json.loads((Path(__file__).resolve().parents[2] / "seeds/platform-starter.json").read_text())
_CODES = ("sca", "plab", "casc", "ortho")


def _v2(code: str) -> dict[str, Any]:
    """A seeded exam's stored (version 2) rubric structure."""
    return next(entry["rubric"]["structure"] for entry in _SEED["exams"] if entry["code"] == code)


def _expected_plab() -> dict[str, Any]:
    seed = _v2("plab")
    cf = seed["sections"][0]["competencyFields"]

    def block(index: int, block_id: str, title: str) -> dict[str, Any]:
        return {
            "block": "domain",
            "id": block_id,
            "title": title,
            "instructions": f"{title} feedback",
            "live": False,
            "scale": "marks",
            "competencies": seed["sections"][index]["competencies"],
            "feedback": [],
        }

    def item(position: int, item_id: str, kind: str, label: str) -> dict[str, Any]:
        return {
            "id": item_id,
            "kind": kind,
            "shape": "list",
            "label": label,
            "required": False,
            "instructions": cf[position]["instructions"],
        }

    return {
        "schemaVersion": 3,
        "instructions": seed["instructions"],
        "mark": {
            "field": "score",
            "label": "Score",
            "required": True,
            "role": "rating",
            "instructions": "Performance score (0.0-1.0) based on GMC standards.",
        },
        "scales": [{"id": "marks", "name": "0 to 1", "from": 0.0, "to": 1.0, "step": "any"}],
        "outline": [
            block(0, "data_gathering", "Data gathering"),
            block(1, "clinical_management", "Clinical management"),
            block(2, "interpersonal_skills", "Interpersonal skills"),
        ],
        "competencyFeedback": [
            item(1, "completed", "strengths", "Completed"),
            item(2, "critical_flags", "flags", "Critical flags"),
            item(3, "missed", "improvements", "Missed"),
            item(4, "suggested_actions", "actions", "Suggested actions"),
            item(5, "supporting_phrase", "quotes", "Supporting phrase"),
        ],
        "pass": {
            "domain": {"score": "sum", "rule": {"type": "score", "atLeast": 2}},
            "overall": {
                "score": "sum",
                "rule": {"type": "score", "atLeast": 7},
                "everyDomainPasses": True,
            },
        },
        "advanced": {
            "tones": seed["display"]["tones"],
            "labels": seed["display"]["labels"],
        },
    }


def test_plab_upgrades_to_the_scheme_an_author_reads() -> None:
    assert scheme.upgrade_v2_to_v3(_v2("plab")) == _expected_plab()


def test_sca_upgrades_to_domains_notes_and_one_custom_item() -> None:
    seed = _v2("sca")
    v3 = scheme.upgrade_v2_to_v3(seed)
    assert [(b["block"], b["id"]) for b in v3["outline"]] == [
        ("domain", "global_skills"),
        ("domain", "tasks"),
        ("domain", "relating_to_others"),
        ("notes", "clinical_analysis"),
        ("notes", "actionable_feedback"),
    ]
    assert v3["scales"] == [{"id": "rag", "name": "RAG", "levels": scheme.RAG_LEVELS}]
    assert "instructions" not in v3
    assert [i["kind"] for i in v3["outline"][3]["feedback"]] == [
        "improvements",
        "strengths",
        "improvements",
        "improvements",
        "flags",
        "note",
        "note",
    ]
    assert v3["outline"][4]["feedback"] == [
        {"id": "overall_priorities", "custom": seed["sections"][4]["fields"][0]}
    ]
    assert [(i["id"], i["kind"], i["shape"]) for i in v3["competencyFeedback"]] == [
        ("supporting_phrase", "quotes", "line"),
        ("score_explanation", "reason", "paragraph"),
    ]
    assert v3["pass"] == {"domain": {"score": "labels"}, "overall": {"score": "labels"}}
    assert v3["advanced"] == {
        "labels": {
            "domainSubtitle": "RAG mix by clinical domain",
            "trendSubtitle": "How your skills moved across recent sessions",
        }
    }
    assert "show" not in v3 and "tone" not in v3
    assert all(b["live"] == (b["id"] != "global_skills") for b in v3["outline"][:3])


def test_casc_keeps_each_domains_own_written_fields_as_custom() -> None:
    seed = _v2("casc")
    v3 = scheme.upgrade_v2_to_v3(seed)
    assert v3["scales"][0] == {
        "id": "competent",
        "name": "Competent / Not competent",
        "levels": scheme.BOOLEAN_LEVELS,
    }
    assert v3["mark"]["field"] == "competent"
    assert v3["mark"]["default"] is False
    assert v3["mark"]["required"] is False
    assert v3["competencyFeedback"] == []
    for block, section in zip(v3["outline"], seed["sections"], strict=True):
        assert block["feedback"] == [{"id": "generic_domains", "custom": section["fields"][0]}]
    rule = {"type": "score", "atLeast": 80}
    assert v3["pass"] == {
        "domain": {"score": "percent", "rule": rule},
        "overall": {"score": "percent", "rule": rule},
    }


def test_ortho_keeps_optional_domains_bands_and_the_station_type_selector() -> None:
    seed = _v2("ortho")
    v3 = scheme.upgrade_v2_to_v3(seed)
    assert v3["outline"][0] == {
        "block": "notes",
        "id": "station_type",
        "single": True,
        "feedback": [{"id": "station_type", "custom": seed["sections"][0]["field"]}],
    }
    for block, section in zip(v3["outline"][1:], seed["sections"][1:], strict=True):
        assert block["optional"] is True
        assert block["advanced"] == {"required": False}
        assert block["description"] == section["description"]
    assert v3["scales"][0] == {"id": "marks", "name": "0 to 10", "from": 0, "to": 10, "step": "whole"}
    assert v3["pass"]["domain"] == {"score": "mean", "rule": {"type": "score", "atLeast": 7}}
    assert v3["pass"]["overall"] == {"score": "sum", "rule": {"type": "score", "atLeast": 35}}
    assert len(v3["advanced"]["bands"]) == 4


@pytest.mark.parametrize("code", _CODES)
def test_every_seed_compiles_back_to_what_it_was(code: str) -> None:
    assert scheme.compile_v3(scheme.upgrade_v2_to_v3(_v2(code))) == domain.upgrade_structure(_v2(code))


@pytest.mark.parametrize("code", _CODES)
def test_every_seed_derives_the_same_schemas_display_and_payload(code: str) -> None:
    before = domain.parse_structure(_v2(code))
    after = domain.parse_structure(scheme.upgrade_v2_to_v3(_v2(code)))
    assert schema_builder.derive_result_schema(before) == schema_builder.derive_result_schema(after)
    assert schema_builder.derive_display_schema(before) == schema_builder.derive_display_schema(after)
    assert domain.resolved_display(before) == domain.resolved_display(after)

    def payload(structure: domain.RubricStructure) -> dict[str, Any]:
        return schema_builder.framework_payload(
            framework_id="f", label="L", version="1", structure=structure, system_prompt="p"
        )

    assert payload(before) == payload(after)
    assert '"points"' not in json.dumps(payload(after))


def test_authoring_form_of_a_v3_is_itself_and_of_v2_is_the_upgrade() -> None:
    v3 = scheme.upgrade_v2_to_v3(_v2("plab"))
    assert domain.authoring_form(v3) == v3
    assert domain.authoring_form(_v2("plab")) == v3
    assert domain.authoring_form(None) == {"schemaVersion": 3, "outline": []}


def test_a_v1_structure_reads_the_same_through_the_scheme() -> None:
    v1 = {
        "scale": ["R", "A", "G"],
        "domains": [{"id": "d", "label": "D", "competencies": [{"id": "c", "label": "C"}]}],
    }
    assert domain.upgrade_structure(domain.authoring_form(v1)) == domain.upgrade_structure(v1)


def test_a_shape_the_blocks_cannot_hold_is_kept_raw() -> None:
    plab = _v2("plab")
    odd = {**plab, "display": {**plab["display"], "weird": 1}}
    assert scheme.upgrade_v2_to_v3(odd) == {"schemaVersion": 3, "advanced": {"raw": odd}}
    assert scheme.compile_v3(scheme.upgrade_v2_to_v3(odd)) == odd


def test_junk_never_raises() -> None:
    junk = scheme.upgrade_v2_to_v3({"schemaVersion": 2, "rating": "x", "sections": "y"})
    assert junk["advanced"]["raw"]["rating"] == "x"


def test_the_blank_v2_keeps_its_implicit_rag_scale() -> None:
    v3 = scheme.upgrade_v2_to_v3(authoring.blank_structure())
    assert v3["advanced"]["ragScaleImplicit"] is True
    assert scheme.compile_v3(v3) == authoring.blank_structure()


def test_the_blank_scheme_compiles_to_a_publishable_rubric() -> None:
    assert domain.parse_structure(authoring.blank_scheme()).rating.kind == "rag"
    compiled = scheme.compile_v3(authoring.blank_scheme())
    assert compiled["sections"][0]["competencyFields"][0] == {
        "id": "score",
        "type": "rating",
        "role": "rating",
        "label": "Rating",
    }


def test_based_on_passes_through() -> None:
    v3 = authoring.with_origin(scheme.upgrade_v2_to_v3(_v2("plab")), rubric_id="r", version=2, title="PLAB 2")
    assert scheme.compile_v3(v3)["basedOn"] == v3["basedOn"]


def test_an_attempt_freezes_the_compiled_form() -> None:
    assert domain.frozen_structure(scheme.upgrade_v2_to_v3(_v2("sca")), None) == domain.frozen_structure(
        _v2("sca"), None
    )
