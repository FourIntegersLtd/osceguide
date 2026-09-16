"""The formatters render exactly the text checked in beside them.

The snapshots started as the legacy ``livekit`` workers' output, byte for byte,
and held that parity through the cutover. The live prompts have since been
rewritten so each persona states its role and holds its clinical material back
until asked, so these files now pin the current prompts rather than the legacy
ones. The feedback and transcript snapshots are still the legacy output: those
formatters did not change.

Regenerate deliberately, never to make a diff go away. A change here changes
what a model is told during a real exam.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from osce_assessment.prompts import (
    ConversationPromptFormatter,
    DebriefPromptFormatter,
    ManagementPlanFormatter,
    OrthoClinicalSkillFeedbackFormatter,
    OrthoCommunicationSkillFeedbackFormatter,
    OrthoFeedbackFormatter,
    OrthoPortfolioSkillFeedbackFormatter,
    OrthoPrioritisationSkillFeedbackFormatter,
    PlabFeedbackFormatter,
    ScaFeedbackFormatter,
    TranscriptFormatter,
    create_org_station_prompt,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load(relative: str) -> dict:
    return json.loads((FIXTURES / relative).read_text(encoding="utf-8"))


def _snapshot(name: str) -> str:
    return (FIXTURES / "prompts" / f"{name}.txt").read_text(encoding="utf-8")


def test_library_station_prompt_matches_snapshot() -> None:
    assert ConversationPromptFormatter.create_prompt(_load("stations/library_station_sca.json")) == _snapshot("library_station_sca")


def test_default_station_prompt_matches_snapshot() -> None:
    assert ConversationPromptFormatter.create_prompt(None) == _snapshot("library_station_default")


def test_org_station_prompt_matches_snapshot() -> None:
    assert create_org_station_prompt(_load("stations/org_station_demo.json")) == _snapshot("org_station_demo")


def test_sca_feedback_rendering_matches_legacy() -> None:
    assert ScaFeedbackFormatter.format(_load("feedback/sca_feedback.json")) == _snapshot("debrief_feedback_sca")


def test_plab_feedback_rendering_matches_legacy() -> None:
    assert PlabFeedbackFormatter.format(_load("feedback/plab_feedback.json")) == _snapshot("debrief_feedback_plab")


def test_ortho_feedback_rendering_matches_legacy() -> None:
    assert OrthoFeedbackFormatter.format(_load("feedback/ortho_feedback.json"), station_type="clinical") == _snapshot(
        "debrief_feedback_ortho_clinical"
    )


@pytest.mark.parametrize(
    ("station_type", "formatter"),
    [
        ("clinical", OrthoClinicalSkillFeedbackFormatter),
        ("prioritisation", OrthoPrioritisationSkillFeedbackFormatter),
        ("communication", OrthoCommunicationSkillFeedbackFormatter),
        ("portfolio", OrthoPortfolioSkillFeedbackFormatter),
        ("unknown", OrthoClinicalSkillFeedbackFormatter),
    ],
)
def test_ortho_station_type_routing(station_type, formatter) -> None:
    feedback = _load("feedback/ortho_feedback.json")
    assert OrthoFeedbackFormatter.format(feedback, station_type=station_type) == formatter.format(feedback)


def test_debrief_prompt_matches_snapshot() -> None:
    sca = _load("feedback/sca_feedback.json")
    prompt = DebriefPromptFormatter.create_prompt(
        transcript="[1] DOCTOR: What's brought you in today?\n[2] PATIENT: This tightness in my chest.",
        management_plan="Assessment: rule out ACS. Explanation: likely stable angina.",
        sca_feedback=ScaFeedbackFormatter.format(sca),
        plab_feedback=PlabFeedbackFormatter.format(sca),
        ortho_feedback="",
        station_type="",
    )
    assert prompt == _snapshot("debrief_prompt_sca")


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


def test_management_plan_renders_sections_or_interview_questions_by_flag() -> None:
    plan = {"explanation": "Likely stable angina.", "immediate_actions": ["ECG today", "Aspirin 300mg"]}
    rendered = ManagementPlanFormatter.format(plan)
    assert rendered.startswith("## Explanation\nLikely stable angina.")
    assert "ECG today\nAspirin 300mg" in rendered
    assert ManagementPlanFormatter.format({}) == ManagementPlanFormatter.DEFAULT_PLAN

    station = {"interview_questions": [{"question": "Tell me about an audit.", "answer": "Closed loop on VTE prophylaxis."}]}
    interview = ManagementPlanFormatter.format(plan, interview_questions=True, station_obj=station)
    assert interview.startswith("## Interview Questions & Answers")
    assert "**Q:** Tell me about an audit." in interview
    assert "Explanation" not in interview

    with_cv = ManagementPlanFormatter.format(None, interview_questions=True, station_obj=station, candidate_cv_markdown="## Summary\nST3 trainee")
    assert with_cv.startswith("## Candidate CV\n## Summary\nST3 trainee")
    assert with_cv.index("Candidate CV") < with_cv.index("Interview Questions")
