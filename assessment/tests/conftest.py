"""Shared fixtures: a definition, an attempt, and a scenario that need no I/O."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from osce_assessment.contracts import (
    AIInteractionProfile,
    AssessmentAttempt,
    AssessmentDefinition,
    EvaluationPolicy,
    InteractionMode,
    Scenario,
    ScenarioRef,
    ScenarioSource,
)
from osce_assessment.testing import example_framework

FRAMEWORK = example_framework()

FIXED_TIME = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def fixed_time() -> datetime:
    return FIXED_TIME


@pytest.fixture
def scenario() -> Scenario:
    return Scenario(
        id="station-chest-pain",
        source=ScenarioSource.LIBRARY,
        title="Chest pain in a 54-year-old",
        patient_brief={"opening_sentence": "I've had this tightness in my chest."},
        patient_gender="male",
        duration_seconds=600,
    )


@pytest.fixture
def definition() -> AssessmentDefinition:
    return AssessmentDefinition(
        id="def-chest-pain",
        version="3",
        framework_id=FRAMEWORK.id,
        scenario_ref=ScenarioRef(source=ScenarioSource.LIBRARY, scenario_id="station-chest-pain"),
        interaction_profile=AIInteractionProfile(
            mode=InteractionMode.PATIENT,
            greeting="Hi doctor.",
            tools=("search_help_faqs",),
        ),
        evaluation_policy=EvaluationPolicy(
            framework_id=FRAMEWORK.id,
            primary_model="primary-model",
            primary_reasoning_effort="low",
            fallback_model="fallback-model",
            version="policy-7",
        ),
        snapshot_at=FIXED_TIME,
    )


@pytest.fixture
def attempt(definition: AssessmentDefinition) -> AssessmentAttempt:
    return AssessmentAttempt(
        attempt_id="attempt-1",
        definition=definition,
        candidate_ref="candidate-42",
        attempt_context={"correlation_a": "a-1", "correlation_b": "b-2"},
    )
