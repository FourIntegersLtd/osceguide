"""The attempt lifecycle and the rules the worker contract depends on.

Invariants A1-A8 from the architecture proposal. The freezing rules are the
important ones: both legacy backends freeze a rendered definition on first
bootstrap, and both freeze it even when the render was degraded.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.features.attempts import domain, domain_definition
from app.features.attempts.domain import Status

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


# --------------------------------------------------------------------------
# A3: the status machine
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (Status.CREATED, Status.RUNNING),
        (Status.RUNNING, Status.INTERACTION_COMPLETE),
        (Status.INTERACTION_COMPLETE, Status.EVALUATED),
        (Status.CREATED, Status.FAILED),
        (Status.RUNNING, Status.FAILED),
        (Status.INTERACTION_COMPLETE, Status.FAILED),
    ],
)
def test_allowed_transitions(start: Status, end: Status) -> None:
    assert domain.transition(start, end) is end


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (Status.EVALUATED, Status.RUNNING),
        (Status.EVALUATED, Status.INTERACTION_COMPLETE),
        (Status.FAILED, Status.RUNNING),
        (Status.CREATED, Status.EVALUATED),
        (Status.RUNNING, Status.EVALUATED),
    ],
)
def test_refused_transitions(start: Status, end: Status) -> None:
    with pytest.raises(domain.InvalidTransition):
        domain.transition(start, end)


def test_an_attempt_cannot_be_completed_twice() -> None:
    """A8. The worker retries delivery, so this is reached in normal operation."""
    with pytest.raises(domain.InvalidTransition):
        domain.transition(Status.INTERACTION_COMPLETE, Status.INTERACTION_COMPLETE)


# --------------------------------------------------------------------------
# A1/A2: freezing the definition
# --------------------------------------------------------------------------


def test_a_definition_freezes_on_a_successful_render() -> None:
    assert domain.should_freeze(render_degraded=False, already_frozen=False)


def test_a_degraded_render_is_never_frozen() -> None:
    """A2, the fix.

    Both backends freeze unconditionally today, so a station that failed to
    resolve pins a generic patient prompt — or a debrief prompt carrying no
    transcript ids, leaving the insights panel empty — to that attempt forever.
    Serve the fallback so the session can run; do not record it.
    """
    assert not domain.should_freeze(render_degraded=True, already_frozen=False)


def test_a_frozen_definition_is_never_replaced() -> None:
    """A1. Re-dispatch replays what was frozen rather than re-rendering against
    today's documents."""
    assert not domain.should_freeze(render_degraded=False, already_frozen=True)


# --------------------------------------------------------------------------
# A7: what the worker may never see
# --------------------------------------------------------------------------


def test_the_bootstrap_payload_never_carries_the_evaluation_policy() -> None:
    definition = {
        "id": "d1",
        "version": 1,
        "framework_id": "sca-rcgp-v1",
        "interaction_profile": {"instructions": "You are the patient."},
        "evaluation_policy": {"primary_model": "gpt-5-mini"},
    }
    payload = domain_definition.bootstrap_definition(definition)
    assert "evaluation_policy" not in payload
    assert payload["interaction_profile"]["instructions"]


def test_a_definition_without_instructions_is_not_servable() -> None:
    """The worker refuses an empty instruction set, so catching it here turns a
    failed job into a clear error at creation time."""
    with pytest.raises(domain.UnrenderableDefinition):
        domain_definition.bootstrap_definition({"id": "d1", "interaction_profile": {"instructions": "  "}})


# --------------------------------------------------------------------------
# A4/A5/A6: idempotency
# --------------------------------------------------------------------------


def test_the_completed_transcript_is_accepted_once() -> None:
    assert domain.should_accept_transcript(already_complete=False)
    assert not domain.should_accept_transcript(already_complete=True)


def test_scoring_is_idempotent_per_policy_version() -> None:
    """A6. Re-scoring under a new policy is a new result, not a replacement."""
    assert not domain.should_score(
        scored_versions={"platform-default@1"}, policy_version="platform-default@1"
    )
    assert domain.should_score(scored_versions={"platform-default@1"}, policy_version="kings-rubric@3")


# --------------------------------------------------------------------------
# Attempt kinds
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# Rendering a definition (A1/A2) — the rules that decide what gets frozen
# --------------------------------------------------------------------------


def test_a_station_with_a_patient_is_renderable() -> None:
    assert domain_definition.scenario_is_renderable({"patient_information": {"persona": "A worried man."}})
    assert domain_definition.scenario_is_renderable({"patient_info": {"name": "Ray", "history": "Smoker."}})


def test_a_station_with_no_usable_patient_content_is_not_renderable() -> None:
    """A patient with nothing to say is the degradation A2 exists to catch.

    It has to be detected before the render rather than inferred from its
    output, which would mean comparing rendered text against a rendering of
    the default and would break the moment either changed.
    """
    assert not domain_definition.scenario_is_renderable({})
    assert not domain_definition.scenario_is_renderable({"patient_information": {}})
    assert not domain_definition.scenario_is_renderable({"patient_information": {"persona": "   "}})
    assert not domain_definition.scenario_is_renderable(None)


# A station written against a template: its block ids are whatever its author
# chose, so the only thing that says what each one is for is the layout.
LAYOUT = [
    {"id": "who_you_are", "label": "Who you are", "role": "persona"},
    {"id": "why_you_came", "label": "Why you came", "role": "complaint"},
    {"id": "expected", "label": "Expected answers", "role": "examiner"},
]


def test_a_templated_station_is_renderable_on_its_own_block_ids() -> None:
    """The regression: this was judged on `patient_information` alone, so every
    station authored against a template was called degraded, never frozen, and
    therefore ran but was never marked."""
    assert domain_definition.scenario_is_renderable(
        {"who_you_are": "Marek, 61, a retired bus driver."}, LAYOUT
    )
    assert domain_definition.scenario_is_renderable({"why_you_came": ["Short of breath."]}, LAYOUT)


def test_a_templated_station_with_only_examiner_material_is_not_renderable() -> None:
    """It looks full and has nothing the patient can say."""
    assert not domain_definition.scenario_is_renderable({"expected": "Should reach COPD."}, LAYOUT)


def test_a_templated_station_whose_patient_blocks_are_empty_is_not_renderable() -> None:
    assert not domain_definition.scenario_is_renderable({"who_you_are": "   "}, LAYOUT)
    assert not domain_definition.scenario_is_renderable({"unrelated": "text"}, LAYOUT)


# An examiner-led viva: the candidate reads the scenario, the examiner asks the questions.
VIVA_LAYOUT = [
    {"id": "clinical_scenario", "label": "Clinical scenario", "role": "candidate_brief"},
    {"id": "interview_questions", "label": "Interview questions", "role": "examiner"},
]


def test_a_viva_is_renderable_on_its_questions() -> None:
    """It has no patient blocks at all; what the examiner asks is what it runs on."""
    content = {
        "clinical_scenario": "A 70-year-old with a hip fracture.",
        "interview_questions": ["Classify it."],
    }
    assert domain_definition.scenario_is_renderable(content, VIVA_LAYOUT, "examiner")
    assert not domain_definition.scenario_is_renderable(content, VIVA_LAYOUT)


def test_a_viva_with_no_questions_is_not_renderable() -> None:
    """The scenario alone leaves the examiner nothing of the station's own to ask."""
    assert not domain_definition.scenario_is_renderable(
        {"clinical_scenario": "A 70-year-old with a hip fracture."}, VIVA_LAYOUT, "examiner"
    )


def test_a_definition_carries_everything_the_worker_and_the_marker_need() -> None:
    payload = domain_definition.definition_payload(
        attempt_id="a-1",
        framework_id="sca-rcgp-v1",
        scenario_source="library",
        scenario_id="station-9",
        scenario={"id": "station-9", "source": "library", "title": "Chest pain"},
        instructions="You are the patient.",
        greeting="Hello doctor.",
        mode="patient",
        policy_version="platform-default@1",
        primary_model="gpt-5-mini",
        at=NOW,
    )

    assert payload["framework_id"] == "sca-rcgp-v1"
    assert payload["scenario_ref"] == {"source": "library", "scenario_id": "station-9"}
    assert payload["interaction_profile"]["instructions"] == "You are the patient."
    assert payload["interaction_profile"]["greeting"] == "Hello doctor."
    assert payload["snapshot_at"] == NOW.isoformat()
    # The marker reads this; the worker never sees it.
    assert payload["evaluation_policy"]["version"] == "platform-default@1"
    assert payload["evaluation_policy"]["primary_model"] == "gpt-5-mini"


def test_a_rendered_definition_survives_the_worker_filter() -> None:
    """The two halves have to agree, or a freshly rendered attempt is refused."""
    payload = domain_definition.definition_payload(
        attempt_id="a-2",
        framework_id="sca-rcgp-v1",
        scenario_source="library",
        scenario_id="s-1",
        scenario={"id": "s-1", "source": "library", "title": "Chest pain"},
        instructions="You are the patient.",
        greeting=None,
        mode="patient",
        policy_version="platform-default@1",
        primary_model="gpt-5-mini",
        at=NOW,
    )

    visible = domain_definition.bootstrap_definition(payload)

    assert "evaluation_policy" not in visible
    assert "scenario" not in visible, "the engine's definition forbids extra keys"
    assert visible["interaction_profile"]["instructions"] == "You are the patient."


def test_the_tools_a_render_names_reach_the_worker_with_their_context() -> None:
    """A debrief names check_time and sends its clock; both must survive the worker filter."""
    pacing = {"total_seconds": 600, "marks": [], "phases": []}
    payload = domain_definition.definition_payload(
        attempt_id="a-4",
        framework_id="sca-rcgp-v1",
        scenario_source="library",
        scenario_id="s-1",
        scenario={"id": "s-1", "source": "library", "title": "Chest pain"},
        instructions="You are the tutor.",
        greeting=None,
        mode="tutor",
        policy_version="platform-default@1",
        primary_model="gpt-5-mini",
        at=NOW,
        tools=("check_time",),
        tool_context={"pacing": pacing},
    )

    profile = domain_definition.bootstrap_definition(payload)["interaction_profile"]

    assert profile["tools"] == ["check_time"]
    assert profile["tool_context"] == {"pacing": {"total_seconds": 600, "marks": [], "phases": []}}


def test_the_scenario_is_frozen_beside_the_definition_and_handed_back() -> None:
    scenario = domain_definition.scenario_payload(
        scenario_id="s-1",
        scenario_source="library",
        title="Chest pain",
        content={"patient_information": {"gender": "Male", "persona": "anxious"}},
    )
    payload = domain_definition.definition_payload(
        attempt_id="a-3",
        framework_id="sca-rcgp-v1",
        scenario_source="library",
        scenario_id="s-1",
        scenario=scenario,
        voice=scenario["patient_gender"],
        instructions="You are the patient.",
        greeting=None,
        mode="patient",
        policy_version="platform-default@1",
        primary_model="gpt-5-mini",
        at=NOW,
    )

    assert domain_definition.worker_scenario(payload) == scenario
    assert payload["interaction_profile"]["voice"] == "male"
    assert scenario["patient_gender"] == "male"
    assert scenario["raw"] == {}, "marking material does not travel with the session"


def test_a_definition_frozen_without_a_scenario_still_yields_one() -> None:
    """Attempts frozen before scenarios were stored must still bootstrap."""
    scenario = domain_definition.worker_scenario(
        {"id": "d1", "scenario_ref": {"source": "org", "scenario_id": "v-9"}}
    )
    assert scenario == {"id": "v-9", "source": "org", "title": ""}


def test_patient_gender_is_read_from_whichever_key_the_station_uses() -> None:
    assert domain_definition.patient_gender({"patient_information": {"gender": "female"}}) == "female"
    assert domain_definition.patient_gender({"patient_info": {"sex": "M"}}) == "male"
    assert domain_definition.patient_gender({"patient_information": {"gender": "Woman"}}) == "female"
    assert domain_definition.patient_gender({"patient_information": {"gender": "nonsense"}}) is None
    assert domain_definition.patient_gender({"patient_information": {"persona": "x"}}) is None
    assert domain_definition.patient_gender({}) is None
    assert domain_definition.patient_gender(None) is None


# --------------------------------------------------------------------------
# The free trial counts stations, not attempts
# --------------------------------------------------------------------------

STATION_ONE, STATION_TWO = uuid.uuid4(), uuid.uuid4()
FIRST_VERSION, SECOND_VERSION, OTHER_VERSION = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
# Two versions of the first station, one of the second.
STATION_BY_VERSION = {FIRST_VERSION: STATION_ONE, SECOND_VERSION: STATION_ONE, OTHER_VERSION: STATION_TWO}


def _trial_attempt(
    version_id: uuid.UUID | None, status: str = "evaluated", kind: str = "practice", started: bool = True
) -> domain.TrialAttempt:
    return domain.TrialAttempt(
        attempt_id=uuid.uuid4(), kind=kind, status=status, station_version_id=version_id, started=started
    )


def test_retrying_a_station_does_not_use_up_another_trial_station() -> None:
    sat = [_trial_attempt(FIRST_VERSION), _trial_attempt(SECOND_VERSION), _trial_attempt(FIRST_VERSION)]

    counts = domain.count_trial_use(
        sat, station_by_version=STATION_BY_VERSION, starting_station_id=STATION_ONE
    )

    assert counts == domain.TrialCounts(
        set_stations=0, completed_stations=1, started_this_station=True, completed_on_this_station=3
    )


def test_an_unfinished_attempt_is_a_start_but_not_a_completion() -> None:
    sat = [_trial_attempt(FIRST_VERSION, status="running"), _trial_attempt(OTHER_VERSION)]

    counts = domain.count_trial_use(
        sat, station_by_version=STATION_BY_VERSION, starting_station_id=STATION_ONE
    )

    assert counts == domain.TrialCounts(
        set_stations=0, completed_stations=1, started_this_station=True, completed_on_this_station=0
    )


def test_a_station_never_sat_is_not_a_retry() -> None:
    sat = [_trial_attempt(FIRST_VERSION)]

    counts = domain.count_trial_use(
        sat, station_by_version=STATION_BY_VERSION, starting_station_id=STATION_TWO
    )

    assert counts.started_this_station is False
    assert counts.completed_on_this_station == 0


def test_a_set_station_that_failed_before_starting_is_free_but_stationless_attempts_each_count() -> None:
    sat = [
        _trial_attempt(FIRST_VERSION, kind="set_station"),
        _trial_attempt(SECOND_VERSION, kind="set_station", status="running"),
        _trial_attempt(OTHER_VERSION, kind="set_station", status="failed", started=False),
        # No station at all: each of these is a station of its own.
        _trial_attempt(None),
        _trial_attempt(None),
    ]

    counts = domain.count_trial_use(sat, station_by_version=STATION_BY_VERSION, starting_station_id=None)

    assert counts == domain.TrialCounts(
        set_stations=1, completed_stations=3, started_this_station=False, completed_on_this_station=0
    )


def test_a_set_station_walked_away_from_after_it_started_still_uses_a_trial_station() -> None:
    sat = [_trial_attempt(OTHER_VERSION, kind="set_station", status="failed", started=True)]

    counts = domain.count_trial_use(sat, station_by_version=STATION_BY_VERSION, starting_station_id=None)

    assert counts.set_stations == 1


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("Male, 45", "male"), ("Mrs.", "female"), ("other", None)],
)
def test_patient_gender_tolerates_the_wordings_stations_really_carry(raw, expected) -> None:
    assert domain_definition.patient_gender({"patient_information": {"gender": raw}}) == expected
