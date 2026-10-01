"""Unit tests for station template content validation."""

from __future__ import annotations

from app.features.stations.station_content import (
    validate_station_content,
)
from app.features.stations.station_validator import validate_station_structure

MINIMAL_STRUCTURE = {
    "schemaVersion": 1,
    "sections": [
        {
            "id": "main",
            "title": "Main",
            "blocks": [
                {"id": "notes", "type": "longText", "label": "Notes", "required": True},
            ],
        },
    ],
}


def test_validate_station_structure_requires_sections() -> None:
    ok, errs = validate_station_structure({})
    assert not ok
    assert any("sections" in e for e in errs)


def test_validate_station_content_requires_required_block() -> None:
    ok, errs = validate_station_content(MINIMAL_STRUCTURE, {})
    assert not ok
    assert any("notes" in e for e in errs)


def test_validate_station_content_accepts_filled_block() -> None:
    ok, errs = validate_station_content(MINIMAL_STRUCTURE, {"notes": "Hello"})
    assert ok
    assert errs == []


RICH_STRUCTURE = {
    "schemaVersion": 1,
    "sections": [
        {
            "id": "main",
            "title": "Main",
            "blocks": [
                {"id": "scans", "type": "media", "label": "Radiographs"},
                {
                    "id": "ward",
                    "type": "records",
                    "label": "Ward list",
                    "fields": [{"key": "age", "label": "Age"}, {"key": "summary", "label": "Summary"}],
                },
                {"id": "viva", "type": "qaList", "label": "Questions"},
                {"id": "order", "type": "groupedList", "label": "Theatre order"},
            ],
        },
    ],
}


def test_rich_block_types_are_valid_structure() -> None:
    assert validate_station_structure(RICH_STRUCTURE) == (True, [])


def test_records_fields_must_name_keys() -> None:
    broken = {
        "sections": [
            {"id": "main", "blocks": [{"id": "ward", "type": "records", "fields": [{"label": "Age"}]}]}
        ]
    }
    ok, errs = validate_station_structure(broken)
    assert not ok
    assert errs == ["sections[0].blocks[0].fields must be a list of {key, label} objects"]


def test_rich_values_in_their_shapes_are_accepted() -> None:
    content = {
        "scans": [
            "https://example.test/a.png",
            {"url": "https://example.test/report.pdf", "kind": "pdf", "caption": "Report"},
        ],
        "ward": [{"age": 71, "summary": "Hip fracture"}],
        "viva": [{"question": "First step?", "answer": "ATLS primary survey"}],
        "order": {"Trauma list": [{"title": "Bed 2", "reasons": ["Open fracture"]}, "Bed 4"]},
    }
    assert validate_station_content(RICH_STRUCTURE, content) == (True, [])


def test_rich_values_in_the_wrong_shape_are_refused() -> None:
    content = {
        "scans": 3,
        "ward": ["Bed 1"],
        "viva": [{"answer": "No question"}],
        "order": {"Trauma list": [{"reasons": ["no title"]}]},
    }
    ok, errs = validate_station_content(RICH_STRUCTURE, content)
    assert not ok
    assert errs == [
        "Block 'scans' must be a media URL, a {url} object, or a list of them",
        "Block 'ward' must be an array of objects",
        "Block 'viva' must be an array of {question, answer} objects",
        "Block 'order' must be an object of groups, each an array of text or {title, reasons}",
    ]


def test_a_grouped_list_names_its_groups_as_text() -> None:
    def structure(groups: object) -> dict:
        block = {"id": "debrief", "type": "groupedList", "label": "Debrief", "groups": groups}
        return {"schemaVersion": 1, "sections": [{"id": "main", "title": "Main", "blocks": [block]}]}

    assert validate_station_structure(structure(["Reaction", "Analysis"]))[0]
    ok, errs = validate_station_structure(structure(["Reaction", ""]))
    assert not ok and any("groups" in e for e in errs)
    assert not validate_station_structure(structure("Reaction"))[0]
