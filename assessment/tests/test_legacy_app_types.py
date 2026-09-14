"""The migration shim: one shared copy of the legacy exam-type translation."""

from __future__ import annotations

import pytest

from osce_assessment.catalog import framework, framework_ids
from osce_assessment.compat import (
    LEGACY_APP_TYPE_TO_FRAMEWORK_ID,
    UnknownAppTypeError,
    framework_id_for_app_type,
    legacy_app_types,
)


def test_the_four_legacy_exam_strings_are_mapped() -> None:
    assert set(legacy_app_types()) == {"sca", "plab", "casc", "ortho"}


@pytest.mark.parametrize(
    ("app_type", "expected"),
    [
        ("sca", "sca-rcgp-v1"),
        ("plab", "plab2-gmc-v1"),
        ("casc", "casc-rcpsych-v1"),
        ("ortho", "ortho-frcs-v1"),
    ],
)
def test_each_exam_string_maps_to_its_framework_id(app_type: str, expected: str) -> None:
    assert framework_id_for_app_type(app_type) == expected


@pytest.mark.parametrize("app_type", ["SCA", " sca ", "Ortho", "ORTHO "])
def test_lookup_tolerates_case_and_whitespace(app_type: str) -> None:
    """Consumers pass this straight from query strings and JWT claims."""
    assert framework_id_for_app_type(app_type) == framework_id_for_app_type(
        app_type.strip().lower()
    )


@pytest.mark.parametrize("app_type", ["", "   ", "employer", "sca-v2", None])
def test_unknown_exam_string_raises_and_names_what_is_known(
    app_type: str | None,
) -> None:
    with pytest.raises(UnknownAppTypeError) as excinfo:
        framework_id_for_app_type(app_type)
    assert "sca" in str(excinfo.value)


def test_every_mapped_id_is_actually_published() -> None:
    """The shim must never point at a framework the catalogue does not have."""
    for framework_id in LEGACY_APP_TYPE_TO_FRAMEWORK_ID.values():
        assert framework_id in framework_ids()
        assert framework(framework_id).id == framework_id


def test_the_shim_returns_an_id_not_a_framework() -> None:
    """Kept as pure data so the shim has no dependency on the catalogue."""
    assert isinstance(framework_id_for_app_type("sca"), str)


def test_the_mapping_table_is_read_only() -> None:
    with pytest.raises(TypeError):
        LEGACY_APP_TYPE_TO_FRAMEWORK_ID["employer"] = "x"  # type: ignore[index]
