"""The dashboard and consulting-doctor prompts render from data alone."""

from __future__ import annotations

from osce_assessment.prompts import AthenaDoctorFormatter, DashboardFeedbackPromptFormatter, ManagementPlanFormatter


def test_dashboard_aggregates_recent_improvements_without_duplicates() -> None:
    feedback = [
        {"created_at": "2026-01-02", "actionable_feedback": {"global_skills_feedback": {"improvements": ["Signpost more", "Signpost more"]}, "tasks_feedback": {"improvements": ["Safety net"]}}},
        {"created_at": "2026-01-01", "actionable_feedback": {"relating_feedback": {"improvements": ["Reflect emotion"]}}},
    ]
    aggregated = DashboardFeedbackPromptFormatter.aggregate_actionable_feedback(feedback)
    assert aggregated == {"global_skills": {"improvements": ["Signpost more"]}, "tasks": {"improvements": ["Safety net"]}, "relating": {"improvements": ["Reflect emotion"]}}
    prompt = DashboardFeedbackPromptFormatter.format_actionable_feedback_for_llm(aggregated)
    assert 'Then gently explore: "Signpost more"' in prompt
    assert 'Then discuss: "Safety net"' in prompt
    assert 'Then explore: "Reflect emotion"' in prompt


def test_dashboard_with_no_feedback_falls_back_to_general_prompts() -> None:
    prompt = DashboardFeedbackPromptFormatter.format_actionable_feedback_for_llm(DashboardFeedbackPromptFormatter.aggregate_actionable_feedback([]))
    assert "Explore general clinical approach" in prompt and "Discuss general task management" in prompt


def test_athena_doctor_prompt_embeds_records_and_the_full_plan() -> None:
    plan = {"assessment": ["Rule out ACS"], "ice": ["Worried about heart"], "explanation": ["Likely stable angina"]}
    prompt = AthenaDoctorFormatter.create_prompt(
        "Chest pain", {"patient_biodata": "Sarah, 54", "recent_notes": ["BP 148/92"], "current_medications": ["Amlodipine"]}, plan
    )
    assert "Working diagnosis / station: Chest pain" in prompt
    assert "Biodata: Sarah, 54" in prompt and "Recent notes: BP 148/92" in prompt
    assert "Current medications: Amlodipine" in prompt
    assert "Rule out ACS" in prompt and "Worried about heart" in prompt
    assert ManagementPlanFormatter.format(plan) in prompt


def test_athena_doctor_interview_variant_uses_station_questions() -> None:
    prompt = AthenaDoctorFormatter.create_prompt("Ortho viva", {}, {}, interview_questions=True)
    assert "Interview Questions" in prompt
