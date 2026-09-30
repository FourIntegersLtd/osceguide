"""The formatters render exactly the text checked in beside them.

The snapshots started as the legacy ``livekit`` workers' output, byte for byte,
and held that parity through the cutover. The live prompts have since been
rewritten so each persona states its role and holds its clinical material back
until asked, so these files now pin the current prompts rather than the legacy
ones. The transcript snapshot is still the legacy output. The marking snapshots
are the one by-role walk every rubric now shares; they replaced the legacy
per-exam formatters' output on 2026-09-30 (rubric templates, Stage 2).

Regenerate deliberately, never to make a diff go away. A change here changes
what a model is told during a real exam.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from osce_assessment.contracts import CompetencyFramework
from osce_assessment.prompts import (
    DashboardTutorFormatter,
    DebriefPromptFormatter,
    ManagementPlanFormatter,
    StationPromptFormatter,
    TranscriptFormatter,
    create_station_prompt,
    render_marking,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load(relative: str) -> dict:
    return json.loads((FIXTURES / relative).read_text(encoding="utf-8"))


def _framework(framework_id: str) -> CompetencyFramework:
    """A framework exactly as platform-api sends it, from `fixtures/frameworks`."""
    return CompetencyFramework.model_validate(_load(f"frameworks/{framework_id}.json"))


def _snapshot(name: str) -> str:
    return (FIXTURES / "prompts" / f"{name}.txt").read_text(encoding="utf-8")


def test_untemplated_station_prompt_matches_snapshot() -> None:
    """No layout: block ids are matched against the common spellings."""
    assert create_station_prompt(_load("stations/untemplated_station.json")) == _snapshot("untemplated_station")


def test_templated_station_prompt_matches_snapshot() -> None:
    """With a layout, the template's own block ids are placed by role."""
    station = _load("stations/templated_station.json")
    assert create_station_prompt(station, station["layout"]) == _snapshot("templated_station")


def test_the_examiner_blocks_never_reach_the_patient() -> None:
    station = _load("stations/templated_station.json")
    prompt = create_station_prompt(station, station["layout"])
    assert "Expected answers" not in prompt and "cessation support" not in prompt
    context = StationPromptFormatter.examiner_context(station, station["layout"])
    assert context is not None and "cessation support" in context


def test_the_examiner_persona_holds_the_examiner_blocks() -> None:
    """An examiner running a viva is given the questions it asks; the patient never is."""
    station = _load("stations/templated_station.json")
    prompt = create_station_prompt(station, station["layout"], persona="examiner")
    assert "<your_questions_and_expected_answers>" in prompt
    assert "cessation support" in prompt
    assert "<your_questions_and_expected_answers>" not in create_station_prompt(station, station["layout"])


@pytest.mark.parametrize(
    ("framework_id", "feedback_fixture", "snapshot_name"),
    [
        ("sca-rcgp-v1", "sca_feedback", "debrief_feedback_sca"),
        ("plab2-v1", "plab_feedback", "debrief_feedback_plab"),
        ("ortho-frcs-v1", "ortho_feedback", "debrief_feedback_ortho"),
    ],
)
def test_marking_rendering_matches_snapshot(framework_id: str, feedback_fixture: str, snapshot_name: str) -> None:
    """One walk by role renders every exam's marking; only the framework differs."""
    rendered = render_marking(_framework(framework_id), _load(f"feedback/{feedback_fixture}.json"))
    assert rendered == _snapshot(snapshot_name)


def test_debrief_prompt_matches_snapshot() -> None:
    sca = _load("feedback/sca_feedback.json")
    prompt = DebriefPromptFormatter.create_prompt(
        transcript="[1] DOCTOR: What's brought you in today?\n[2] PATIENT: This tightness in my chest.",
        management_plan="Assessment: rule out ACS. Explanation: likely stable angina.",
        marking=render_marking(_framework("sca-rcgp-v1"), sca),
    )
    assert prompt == _snapshot("debrief_prompt_sca")


def test_dashboard_tutor_prompt_matches_snapshot() -> None:
    """A change here changes what a learner's tutor is allowed to claim to remember."""
    prompt = DashboardTutorFormatter.create_prompt(_load("tutor/brief.json"), labels={"summaries": "A to Z", "slides": "Slides", "stations": "AI Practice"})
    assert prompt == _snapshot("dashboard_tutor")


def test_transcript_formatter_labels_speakers_and_drops_empty_turns() -> None:
    transcript = {
        "transcript_message": [
            {"role": "user", "message": "What brings you in?", "transcript_message_id": "uuid-a"},
            {"role": "assistant", "message": "  Chest tightness.  ", "transcript_message_id": "uuid-b"},
            {"role": "assistant", "message": "   ", "transcript_message_id": "uuid-c"},
        ]
    }
    text = TranscriptFormatter.format(transcript)
    assert text == "## Consultation Transcript\n\n## Doctor\nWhat brings you in?\n\n## Patient\nChest tightness."
    # The msg_N ids existed only for the retired highlight tool.
    assert "msg_" not in text and "ID:" not in text
    assert TranscriptFormatter.format({"transcript_message": []}) == TranscriptFormatter.DEFAULT_TRANSCRIPT


def test_management_plan_renders_its_sections() -> None:
    plan = {"explanation": "Likely stable angina.", "immediate_actions": ["ECG today", "Aspirin 300mg"]}
    rendered = ManagementPlanFormatter.format(plan)
    assert rendered.startswith("## Explanation\nLikely stable angina.")
    assert "ECG today\nAspirin 300mg" in rendered
    assert ManagementPlanFormatter.format({}) == ManagementPlanFormatter.DEFAULT_PLAN
