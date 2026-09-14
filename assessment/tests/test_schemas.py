"""Marking schemas are data shipped with the engine and attached to the catalogue."""

from __future__ import annotations

import pytest

from osce_assessment.catalog import all_frameworks, framework_ids
from osce_assessment.schemas import UnknownSchemaError, available_schema_ids, load_schema


def test_every_catalogue_framework_has_a_schema_file_and_vice_versa() -> None:
    assert set(available_schema_ids()) == set(framework_ids())


@pytest.mark.parametrize("fw", all_frameworks(), ids=lambda fw: fw.id)
def test_each_framework_carries_its_schema_as_data(fw) -> None:
    assert fw.result_schema == load_schema(fw.id)
    assert fw.result_schema["type"] == "object"
    assert fw.result_schema["properties"]
    assert fw.result_schema["required"]


@pytest.mark.parametrize("fw", all_frameworks(), ids=lambda fw: fw.id)
def test_schemas_carry_no_storage_metadata(fw) -> None:
    """The model is asked for marking content only; ids and timestamps are the consumer's."""
    metadata = {"feedback_id", "user_id", "mock_id", "station_id", "created_at", "updated_at",
                "evaluated_by", "attempt_id", "likes", "liked_by"}
    assert not metadata & set(fw.result_schema["properties"])
    assert not metadata & set(fw.result_schema["required"])


def test_load_schema_returns_an_independent_copy() -> None:
    first = load_schema("sca-rcgp-v1")
    first["properties"].clear()
    assert load_schema("sca-rcgp-v1")["properties"]


def test_unknown_framework_has_no_schema() -> None:
    with pytest.raises(UnknownSchemaError, match="sca-rcgp-v1"):
        load_schema("employer-bespoke-v1")
