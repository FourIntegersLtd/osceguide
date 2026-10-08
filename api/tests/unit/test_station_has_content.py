from app.features.stations.service_versions import _has_content


def test_nothing_written_is_not_content() -> None:
    assert _has_content({}) is False
    assert _has_content({"patient_information": {}, "notes": "  ", "list": [[], ""]}) is False
    assert _has_content(None) is False


def test_any_written_value_is_content() -> None:
    assert _has_content({"patient_information": {"persona": "anxious"}}) is True
    assert _has_content({"a": [{"b": " x "}]}) is True


def test_zero_and_false_count_as_content() -> None:
    """A number or a flag someone set is an answer, not a blank."""
    assert _has_content({"age": 0}) is True
    assert _has_content({"flag": False}) is True
