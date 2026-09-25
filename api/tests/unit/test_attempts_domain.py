"""The attempt lifecycle and the rules the worker contract depends on.

Invariants A1-A8 from the architecture proposal. The freezing rules are the
important ones: both legacy backends freeze a rendered definition on first
bootstrap, and both freeze it even when the render was degraded.
"""

from __future__ import annotations

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


def test_a_repeated_chunk_is_ignored_rather_than_appended() -> None:
    """A4. Chunk posts repeat: the worker retries and does not read the response."""
    seen = {"m1", "m2"}
    assert not domain.should_store_chunk("m1", seen)
    assert domain.should_store_chunk("m3", seen)


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
    assert domain_definition.patient_gender({"patient_information": {"persona": "x"}}) is None
    assert domain_definition.patient_gender({}) is None
    assert domain_definition.patient_gender(None) is None
