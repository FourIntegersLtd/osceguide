"""Unit tests for station template content validation."""

from __future__ import annotations

from app.features.stations.station_validator import (
    validate_station_content,
    validate_station_structure,
)

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
