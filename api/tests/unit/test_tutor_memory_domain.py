"""The rules about remembering, with no database in sight."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from app.features.rubrics import domain as rubric_domain
from app.features.rubrics import service_scoring as rubric_scoring
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


class Grant:
    """`entitlements.schemas.EntitlementRead`, as this rule sees one.

    `live` is the field that matters: the entitlements repository returns
    *every* row a person has ever held, revoked and expired included, and the
    service computes `live` per row rather than filtering.
    """

    def __init__(self, exam_id: object, *, live: bool = True) -> None:
        self.exam_id = exam_id
        self.live = live


def test_entitled_exam_ids_drops_duplicates_and_blanks() -> None:
    assert domain.entitled_exam_ids([Grant("a"), Grant("a"), Grant(None)]) == frozenset({"a"})


def test_a_revoked_or_expired_entitlement_unlocks_nothing() -> None:
    """The gate. `list_for_user` returns dead rows, so this rule has to drop them.

    Revoking does not delete: `entitlements.repository.revoke` sets
    `revoked_at` and the row stays, so a rule that reads `exam_id` off every
    grant hands a lapsed subscriber the same set as a paying one — and this
    frozenset becomes the `WHERE exam_id IN (...)` the material search is
    filtered by, and the list `suggest_material` checks a station against.
    """
    assert domain.entitled_exam_ids([Grant("a", live=False)]) == frozenset()
    assert domain.entitled_exam_ids([Grant("a", live=False), Grant("b", live=True)]) == frozenset({"b"})


def test_a_grant_that_cannot_say_whether_it_is_live_is_refused() -> None:
    """Fails closed, deliberately.

    The alternative — treating a missing flag as live — means a caller who
    passes raw `Entitlement` rows instead of the service's read model silently
    unlocks everything, and nothing anywhere would say so.
    """

    class Row:
        exam_id = "a"

    assert domain.entitled_exam_ids([Row()]) == frozenset()


def _seeded(exam_code: str) -> tuple[Any, dict[str, Any]]:
    """A seeded exam's parsed rubric structure and resolved display."""
    seed = json.loads((Path(__file__).resolve().parents[2] / "seeds/platform-starter.json").read_text())
    raw = next(entry["rubric"]["structure"] for entry in seed["exams"] if entry["code"] == exam_code)
    structure = rubric_domain.parse_structure(raw)
    return structure, rubric_domain.resolved_display(structure)


def _observe(structure: Any, display: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """The brief's observations of a result, read the way `service_brief` reads it."""
    return domain.observations_from_result(
        rubric_scoring.weakest_domain_tones(structure, display, payload),
        rubric_scoring.texts_by_role(structure, payload, roles=domain.BRIEF_KEY_FOR_ROLE),
    )


def test_observations_read_an_sca_marking_by_role() -> None:
    structure, display = _seeded("sca")
    payload = {
        "global_skills": {
            "structures_consultation": {"score": "G", "supporting_phrase": "Let me summarise"},
            "avoids_repetition": {"score": "A", "supporting_phrase": "So as I said"},
        },
        "tasks": {"opens_consultation": {"score": "R", "supporting_phrase": "What brings you in?"}},
        "clinical_analysis": {"key_positives": ["Asked about red flags"], "missed_history": ["Smoking"]},
        "actionable_feedback": {"overall_priorities": ["Signpost"], "tasks_feedback": "not read"},
    }
    observed = _observe(structure, display, payload)
    # The weakest rating per domain, as the display's word: never a number.
    assert observed["domains"] == {"Global skills": "fair", "Tasks": "poor"}
    assert observed["strengths"] == ["Asked about red flags"]
    assert observed["improvements"] == ["Smoking", "Signpost"]
    assert observed["phrases"] == ["Let me summarise", "So as I said", "What brings you in?"]


def test_observations_read_a_scored_exam_and_skip_a_null_domain() -> None:
    structure, display = _seeded("ortho")
    payload = {
        "station_type": "clinical",
        "clinical_skills": {
            "technical_knowledge_clinical_expertise": {
                "score": 8,
                "completed": ["Examined the knee"],
                "evidence_points": ["Checked the neurovascular status"],
                "suggested_actions": ["Name the classification"],
            },
            "situational_awareness": {"score": 5},
        },
        "communication_skills": None,
    }
    observed = _observe(structure, display, payload)
    assert observed["domains"] == {"Clinical skills": "fair"}
    assert observed["strengths"] == ["Examined the knee"]
    assert observed["improvements"] == ["Name the classification"]
    assert observed["phrases"] == ["Checked the neurovascular status"]


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


# --------------------------------------------------------------------------
# The tool vocabulary against the corpora the index actually stores. These two
# drifted once already: the tool advertised `management_plan` and the index
# stored `station`, so narrowing a search to a station's management plan
# matched nothing — and read, to the doctor, as the material not covering it.
# --------------------------------------------------------------------------


def test_every_kind_the_model_may_ask_for_names_a_corpus_that_is_indexed() -> None:
    from app.features.tutor_memory import service_material, tools_catalog

    indexed = {service_material.STATION_CORPUS, *domain.MEDIA_KINDS, service_material.HELP_CORPUS}

    for kind in tools_catalog.CORPUS_BY_KIND:
        assert tools_catalog.corpus_for(kind) in indexed, f"{kind} narrows to nothing"


def test_the_advertised_enum_is_exactly_the_kinds_that_map() -> None:
    """A kind in the schema with no mapping would be accepted and then ignored."""
    from app.features.tutor_memory import tools_catalog

    schema = tools_catalog.schema_for(tools_catalog.SEARCH_MATERIAL)
    assert schema is not None
    assert set(schema["properties"]["kind"]["enum"]) == {
        *tools_catalog.CORPUS_BY_KIND,
        tools_catalog.ANY_KIND,
    }


def test_any_is_not_a_corpus() -> None:
    """Passing it through as one would filter every passage out."""
    from app.features.tutor_memory import tools_catalog

    assert tools_catalog.corpus_for(tools_catalog.ANY_KIND) is None


def test_every_indexed_corpus_is_one_the_table_allows() -> None:
    """The CHECK constraint is the backstop; this is the error message."""
    from app.features.tutor_memory import service_material

    allowed = {"station", "summary", "slide_deck", "podcast", "blog"}
    assert {service_material.STATION_CORPUS, *domain.MEDIA_KINDS} <= allowed


class TestMarkingAnActionItemDone:
    """T-4: `done` was written false by the summariser and set true by nothing.

    So `open_action_items` never filtered anything, and the tutor's brief
    listed every step ever agreed, for ever. It degraded rather than failed,
    which is exactly why it survived so long.
    """

    def test_a_step_is_ticked_off_by_its_own_words(self) -> None:
        plan = [{"text": "Safety-net chest pain explicitly", "done": False}]
        updated, matched = domain.mark_action_item_done(plan, "Safety-net chest pain explicitly")
        assert matched == "Safety-net chest pain explicitly"
        assert updated[0]["done"] is True

    def test_a_paraphrase_still_finds_it(self) -> None:
        # The tutor asks aloud and the doctor answers in their own words, so
        # the model passes back a paraphrase. Exact equality would tick off
        # nothing, which is the state this is fixing.
        plan = [{"text": "Safety-net chest pain explicitly", "done": False}]
        _, matched = domain.mark_action_item_done(plan, "safety-net chest pain")
        assert matched == "Safety-net chest pain explicitly"

    def test_a_bare_string_plan_is_accepted(self) -> None:
        # What the model returns when it ignores the schema's optional flag.
        updated, matched = domain.mark_action_item_done(["Read the asthma summary"], "asthma summary")
        assert matched == "Read the asthma summary"
        assert updated[0] == {"text": "Read the asthma summary", "done": True}

    def test_nothing_matching_leaves_the_plan_alone(self) -> None:
        # Ticking off the wrong step is worse than ticking off none: the
        # doctor is then asked about the thing they did, and never about the
        # thing they did not.
        plan = [{"text": "Safety-net chest pain", "done": False}]
        updated, matched = domain.mark_action_item_done(plan, "practise a cardiology station")
        assert matched is None
        assert updated[0]["done"] is False

    def test_only_the_first_open_match_is_ticked(self) -> None:
        plan = [
            {"text": "Safety-net chest pain", "done": True},
            {"text": "Safety-net headache", "done": False},
        ]
        updated, matched = domain.mark_action_item_done(plan, "safety-net")
        assert matched == "Safety-net headache"
        assert [item["done"] for item in updated] == [True, True]

    def test_an_empty_step_ticks_nothing(self) -> None:
        plan = [{"text": "Read the asthma summary", "done": False}]
        updated, matched = domain.mark_action_item_done(plan, "   ")
        assert matched is None
        assert updated == plan

    def test_a_ticked_item_stops_appearing_in_the_brief(self) -> None:
        """The two rules have to agree, or the fix does nothing visible."""
        plan = [{"text": "Read the asthma summary", "done": False}]
        assert domain.open_action_items([plan]) == ["Read the asthma summary"]
        updated, _ = domain.mark_action_item_done(plan, "asthma summary")
        assert domain.open_action_items([updated]) == []


def _opening(seed: int, **brief: Any) -> str:
    import random

    from app.features.tutor_memory import service_session

    brief = {"learner": {"name": "Ada Lovelace"}, **brief}
    return service_session.greeting_for(brief, rng=random.Random(seed))  # noqa: S311 - test draw


def test_a_topic_session_opens_with_one_of_the_topic_greetings_and_they_vary() -> None:
    """The same opening every session reads as a script (C-37)."""
    from app.features.tutor_memory import service_session

    topic = {"title": "Asthma in adults?"}
    expected = {t.format(name=", Ada", topic="Asthma in adults") for t in service_session.GREETINGS_TOPIC}
    draws = [_opening(i, topic=topic) for i in range(20)]
    assert 6 <= len(service_session.GREETINGS_TOPIC) <= 8
    assert set(draws) <= expected
    assert len(set(draws)) > 1


def test_a_returning_session_opens_with_one_of_the_return_greetings_and_they_vary() -> None:
    from app.features.tutor_memory import service_session

    expected = {t.format(name=", Ada") for t in service_session.GREETINGS_RETURNING}
    draws = [_opening(i, last_conversation={"summary": "x"}) for i in range(20)]
    assert 4 <= len(service_session.GREETINGS_RETURNING) <= 5
    assert set(draws) <= expected
    assert len(set(draws)) > 1
