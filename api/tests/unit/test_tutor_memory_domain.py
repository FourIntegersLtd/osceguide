"""The rules about remembering, with no database in sight."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.features.tutor_memory import domain

NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


def test_the_first_sighting_of_anything_is_recorded() -> None:
    assert domain.should_record_event(last_seen_at=None, now=NOW)


def test_coming_straight_back_is_the_same_visit() -> None:
    assert not domain.should_record_event(last_seen_at=NOW - timedelta(minutes=3), now=NOW)


def test_returning_later_is_a_new_visit() -> None:
    assert domain.should_record_event(last_seen_at=NOW - timedelta(minutes=11), now=NOW)


def test_days_ago_never_goes_negative() -> None:
    """A clock that drifted backwards reads as today, not as the future."""
    assert domain.days_ago(NOW + timedelta(hours=5), NOW) == 0
    assert domain.days_ago(NOW - timedelta(days=9), NOW) == 9


def test_a_dashboard_conversation_is_summarised_not_kept_and_not_thrown_away() -> None:
    assert domain.transcript_policy("dashboard") is domain.TranscriptPolicy.SUMMARISE
    assert domain.transcript_policy("help") is domain.TranscriptPolicy.RETAIN
    assert domain.transcript_policy("onboarding") is domain.TranscriptPolicy.DISCARD


def test_an_unknown_session_type_is_discarded() -> None:
    """The safe side to err on: keeping a recording nobody asked for is worse."""
    assert domain.transcript_policy("something-new") is domain.TranscriptPolicy.DISCARD


def test_only_a_finished_debrief_is_worth_summarising() -> None:
    assert domain.should_summarise_attempt(kind="debrief", complete=True)
    assert not domain.should_summarise_attempt(kind="debrief", complete=False)
    assert not domain.should_summarise_attempt(kind="practice", complete=True)


def test_a_long_fact_is_clipped_to_something_sayable() -> None:
    clipped = domain.clip_fact("word " * 200)
    assert len(clipped) <= domain.MAX_FACT_CHARS
    assert clipped.endswith("…")


def test_whitespace_in_a_fact_is_tidied() -> None:
    assert domain.clip_fact("  their   exam\nis in June ") == "their exam is in June"


def test_open_action_items_skips_what_was_ticked_off() -> None:
    plans = [[{"text": "Ask about red flags", "done": True}, {"text": "Set a timeframe", "done": False}]]
    assert domain.open_action_items(plans) == ["Set a timeframe"]


def test_open_action_items_accepts_a_bare_string() -> None:
    """What the model returns when it ignores the schema's optional flag."""
    assert domain.open_action_items([["Say one follow-up timeframe"]]) == ["Say one follow-up timeframe"]


def test_entitled_exam_ids_drops_duplicates_and_blanks() -> None:
    class Grant:
        def __init__(self, exam_id: object) -> None:
            self.exam_id = exam_id

    assert domain.entitled_exam_ids([Grant("a"), Grant("a"), Grant(None)]) == frozenset({"a"})


def test_observations_read_a_marking_as_the_brief_says_it() -> None:
    payload = {
        "domains": [{"name": "clinical approach", "rating": "A"}, {"name": "tasks", "grade": "R"}],
        "strengths": [{"text": "Warm opening"}],
        "areas_for_improvement": ["No examination offered"],
        "quotes": ["Come back if it does not improve"],
        "overall_score": 17,
    }
    observed = domain.observations_from_result(payload)
    assert observed["domains"] == {"clinical approach": "A", "tasks": "R"}
    assert observed["strengths"] == ["Warm opening"]
    assert observed["improvements"] == ["No examination offered"]
    assert observed["phrases"] == ["Come back if it does not improve"]
    assert "overall_score" not in observed


def test_observations_accept_domains_as_a_mapping() -> None:
    observed = domain.observations_from_result({"domains": {"tasks": "G"}})
    assert observed["domains"] == {"tasks": "G"}


SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "maxLength": 10},
        "kind": {"type": "string", "enum": ["note", "any"]},
        "limit": {"type": "integer", "minimum": 1, "maximum": 5},
    },
    "required": ["query"],
}


def test_a_valid_call_comes_back_tidied() -> None:
    assert domain.validate_tool_arguments(SCHEMA, {"query": "  hip   pain ", "limit": 2}) == {
        "query": "hip pain",
        "limit": 2,
    }


def test_an_invented_argument_is_refused() -> None:
    with pytest.raises(domain.InvalidToolArguments, match="unknown"):
        domain.validate_tool_arguments(SCHEMA, {"query": "x", "colour": "red"})


def test_a_missing_required_argument_is_refused() -> None:
    with pytest.raises(domain.InvalidToolArguments, match="missing"):
        domain.validate_tool_arguments(SCHEMA, {"limit": 2})


def test_a_value_outside_the_enum_is_refused() -> None:
    """A kind that means nothing produces an answer about the wrong thing."""
    with pytest.raises(domain.InvalidToolArguments, match="one of"):
        domain.validate_tool_arguments(SCHEMA, {"query": "x", "kind": "everything"})


def test_a_number_outside_its_range_is_refused() -> None:
    with pytest.raises(domain.InvalidToolArguments, match="at most"):
        domain.validate_tool_arguments(SCHEMA, {"query": "x", "limit": 50})


def test_a_number_that_is_not_one_is_refused() -> None:
    with pytest.raises(domain.InvalidToolArguments, match="whole number"):
        domain.validate_tool_arguments(SCHEMA, {"query": "x", "limit": "lots"})


def test_an_overlong_string_is_clipped_rather_than_refused() -> None:
    cleaned = domain.validate_tool_arguments(SCHEMA, {"query": "a" * 40})
    assert len(cleaned["query"]) == 10
