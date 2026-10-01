"""Which account columns a profile update writes, and which it leaves alone."""

from __future__ import annotations

from datetime import date, time

from app.features.identity.schemas import UpdateMe
from app.features.identity.service import profile_changes


def _changes(payload: dict[str, object], exam_code: str | None = None) -> dict[str, object]:
    """The changes for a request body as the route sees it: only the keys sent count as sent."""
    body = UpdateMe.model_validate(payload)
    return profile_changes(body, set(body.model_fields_set), exam_code=exam_code)


def test_a_field_that_was_not_sent_is_not_touched() -> None:
    assert _changes({"name": "Ada"}) == {"name": "Ada"}
    assert _changes({}) == {}


def test_a_set_only_field_sent_as_nothing_is_left_alone() -> None:
    assert _changes({"name": None, "ai_training_consent": None, "needs_extra_time": None}) == {}
    assert _changes({"ai_training_consent": False}) == {"ai_training_consent": False}


def test_a_custom_timer_sent_as_nothing_is_cleared() -> None:
    assert _changes({"custom_reading_seconds": None, "custom_simulation_seconds": 600}) == {
        "custom_reading_seconds": None,
        "custom_simulation_seconds": 600,
    }


def test_clearing_the_exam_date_clears_the_time_even_when_a_time_was_sent() -> None:
    assert _changes({"exam_date": None}) == {"exam_date": None, "exam_time": None}
    assert _changes({"exam_date": None, "exam_time": "09:30"}) == {"exam_date": None, "exam_time": None}


def test_a_date_and_a_time_are_set_or_cleared_independently_while_the_date_stays() -> None:
    assert _changes({"exam_date": "2027-01-12", "exam_time": "09:30"}) == {
        "exam_date": date(2027, 1, 12),
        "exam_time": time(9, 30),
    }
    assert _changes({"exam_time": None}) == {"exam_time": None}


def test_the_exam_is_written_only_when_one_was_decided() -> None:
    assert _changes({"exam_code": "plab"}) == {}
    assert _changes({}, exam_code="plab") == {"exam_code": "plab"}
