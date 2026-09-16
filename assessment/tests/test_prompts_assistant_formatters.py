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
    assert "What you noticed: Signpost more" in prompt
    assert "What you noticed: Safety net" in prompt
    assert "What you noticed: Reflect emotion" in prompt


def test_dashboard_with_no_feedback_asks_rather_than_inventing_observations() -> None:
    """With nothing observed the coach opens the area as a question; it never claims to have seen something."""
    prompt = DashboardFeedbackPromptFormatter.format_actionable_feedback_for_llm(DashboardFeedbackPromptFormatter.aggregate_actionable_feedback([]))
    assert "Ask how they feel their clinical approach is going." in prompt
    assert "Ask what they find hardest about clinical tasks." in prompt
    assert "What you noticed" not in prompt


def test_dashboard_prompt_states_the_role_and_does_not_open_with_a_greeting() -> None:
    """The session speaks the greeting, so the prompt opening its own line made the coach repeat itself."""
    prompt = DashboardFeedbackPromptFormatter.format_actionable_feedback_for_llm(
        DashboardFeedbackPromptFormatter.aggregate_actionable_feedback([])
    )
    assert "<role>" in prompt
    assert "You have already greeted them" in prompt
    assert "We've had a chance to observe" not in prompt


def test_athena_doctor_prompt_embeds_records_and_the_full_plan() -> None:
    plan = {"assessment": ["Rule out ACS"], "ice": ["Worried about heart"], "explanation": ["Likely stable angina"]}
    prompt = AthenaDoctorFormatter.create_prompt(
        "Chest pain", {"patient_biodata": "Sarah, 54", "recent_notes": ["BP 148/92"], "current_medications": ["Amlodipine"]}, plan
    )
    assert "Working diagnosis / station: Chest pain" in prompt
    assert "Biodata: Sarah, 54" in prompt and "Recent notes:\n  - BP 148/92" in prompt
    assert "Current medications:\n  - Amlodipine" in prompt
    assert "Rule out ACS" in prompt and "Worried about heart" in prompt
    assert ManagementPlanFormatter.format(plan) in prompt


def test_athena_doctor_interview_variant_uses_station_questions() -> None:
    prompt = AthenaDoctorFormatter.create_prompt("Ortho viva", {}, {}, interview_questions=True)
    assert "Interview Questions" in prompt


def _numbered_block(prompt: str, marker: str) -> list[str]:
    """The one numbered list that follows a marker line, stopping where it ends."""
    titles: list[str] = []
    for line in prompt[prompt.index(marker):].split("\n")[1:]:
        stripped = line.strip()
        if stripped[:1].isdigit() and ". " in stripped:
            titles.append(stripped.split(". ", 1)[1])
        elif titles:
            break
    return titles


PLAN = {
    "explanation": "x", "differential_diagnosis": ["d"], "assessment": ["a"],
    "further_investigations": ["i"], "ice": ["c"], "immediate_actions": ["im"],
    "pharmacological_treatment": ["p"], "non_pharmacological_treatment": ["np"],
    "follow_up": "f", "health_education": ["he"], "safety_netting": "sn",
}


def test_the_consulting_doctor_is_told_what_the_patient_must_not_leave_without() -> None:
    """The feature exists so a learner experiences a well-run consultation.

    Reciting every heading at the cost of being understood fails at the thing it
    was for, so the plan is split: a spine that must be covered, content worth
    dropping when the conversation needs the room, and notes the patient never
    hears.
    """
    prompt = AthenaDoctorFormatter.create_prompt("Hypothyroidism", {"patient_biodata": "Jane, 44"}, PLAN)
    must = _numbered_block(prompt, "These must be covered before you close")
    if_time = _numbered_block(prompt, "Cover these as well if the conversation makes room")
    notes = _numbered_block(prompt, "These are your own notes")

    assert must == ManagementPlanFormatter.section_titles(PLAN, audience="patient", priority="core")
    assert if_time == ManagementPlanFormatter.section_titles(PLAN, audience="patient", priority="if_time")
    assert notes == ManagementPlanFormatter.section_titles(PLAN, audience="doctor")
    # the spine of any consultation: what is wrong, what is being done, what to watch for
    assert {"Explanation", "Pharmacological Treatment", "Follow-up", "Safety Netting"} <= set(must)
    assert "Assessment" in notes and "Assessment" not in must + if_time


def test_the_three_lists_together_are_the_whole_plan() -> None:
    prompt = AthenaDoctorFormatter.create_prompt("Hypothyroidism", {"patient_biodata": "Jane, 44"}, PLAN)
    every = sum(
        (_numbered_block(prompt, marker) for marker in (
            "These must be covered before you close",
            "Cover these as well if the conversation makes room",
            "These are your own notes",
        )), []
    )
    assert sorted(every) == sorted(ManagementPlanFormatter.section_titles(PLAN))


def test_the_doctor_is_told_to_follow_the_patient_rather_than_the_list() -> None:
    prompt = AthenaDoctorFormatter.create_prompt("Hypothyroidism", {"patient_biodata": "Jane, 44"}, PLAN)
    assert "Follow the patient" in prompt
    assert "worth more than eight things listed" in prompt
    # the instructions that produced the racing cadence are gone
    assert "cover EVERY bullet" not in prompt
    assert "Do NOT enter Phase 4 until every non-empty section" not in prompt


def test_every_section_is_addressed_to_someone_and_given_a_priority() -> None:
    """An untagged heading would silently vanish from every list."""
    every = ManagementPlanFormatter.section_titles(PLAN)
    by_audience = (
        ManagementPlanFormatter.section_titles(PLAN, audience="patient")
        + ManagementPlanFormatter.section_titles(PLAN, audience="doctor")
    )
    assert sorted(by_audience) == sorted(every)
    patient = ManagementPlanFormatter.section_titles(PLAN, audience="patient")
    by_priority = (
        ManagementPlanFormatter.section_titles(PLAN, audience="patient", priority="core")
        + ManagementPlanFormatter.section_titles(PLAN, audience="patient", priority="if_time")
    )
    assert sorted(by_priority) == sorted(patient)


def test_a_sparse_plan_gets_a_checklist_of_only_what_it_has() -> None:
    plan = {"explanation": "x", "safety_netting": "sn"}
    assert ManagementPlanFormatter.section_titles(plan) == ["Explanation", "Assessment", "Safety Netting"]
    assert ManagementPlanFormatter.section_titles(plan, audience="patient") == ["Explanation", "Safety Netting"]


def test_the_doctor_is_not_given_a_responsiveness_rule() -> None:
    """Tried and measured away: it raised breaches from 2.2 to 3.8 per consultation.

    The doctor does race ahead of the patient, but adding a rule against it to an
    already over-constrained prompt made things worse rather than better. The
    racing comes from the exhaustive-coverage instruction itself.
    """
    prompt = AthenaDoctorFormatter.create_prompt("Hypothyroidism", {"patient_biodata": "Jane, 44"}, PLAN)
    assert "<answer_what_was_asked>" not in prompt


def test_an_interview_station_is_pointed_at_its_questions_instead() -> None:
    """Ortho stations render interview Q&A, not plan sections, so a section list would be wrong."""
    prompt = AthenaDoctorFormatter.create_prompt(
        "Ortho", {"patient_biodata": "x"}, {"explanation": "y"}, interview_questions=True
    )
    assert "Work through the interview questions below in the order they appear." in prompt


def test_every_list_item_is_a_bullet_including_the_first() -> None:
    """Joining on the separator left the first item bare and the rest hanging under it.

    "Explore fatigue, weight change and constipation / - Check mood" read as a
    sentence with sub-points rather than as three things to ask about.
    """
    assert AthenaDoctorFormatter.format_list_items(["Check mood", "Ask about neck swelling"]) == (
        "  - Check mood\n  - Ask about neck swelling"
    )
    assert AthenaDoctorFormatter.format_list_items([], "None recorded") == "None recorded"


def test_a_record_label_does_not_share_a_line_with_its_first_entry() -> None:
    prompt = AthenaDoctorFormatter.create_prompt(
        "Hypothyroidism",
        {"patient_biodata": "Jane, 44", "recent_notes": ["TSH raised"], "current_medications": ["Ferrous fumarate"]},
        PLAN,
    )
    assert "Recent notes:\n  - TSH raised" in prompt
    assert "Current medications:\n  - Ferrous fumarate" in prompt


def test_the_plan_reference_does_not_contradict_what_to_cover() -> None:
    """The header told it to deliver every item; the block above told it to prioritise."""
    prompt = AthenaDoctorFormatter.create_prompt("Hypothyroidism", {"patient_biodata": "Jane, 44"}, PLAN)
    assert "deliver EVERY item below to the patient" not in prompt
    assert "Use WHAT TO COVER above" in prompt


def test_the_history_phase_is_not_handed_a_list_of_questions_to_read() -> None:
    """Assessment and ICE are marking criteria, and they already appear in the plan.

    Inlining them made history-taking a script to read rather than something the
    doctor derives from its differentials, which is the behaviour the feature
    exists to model. They remain available in the reference plan.
    """
    prompt = AthenaDoctorFormatter.create_prompt(
        "Hypothyroidism", {"patient_biodata": "Jane, 44"},
        {**PLAN, "assessment": ["Check mood"], "ice": ["Worried about cancer"]},
    )
    assert "Ask about each of these during the history" not in prompt
    assert "The records and the plan tell you what" in prompt
    assert "to weigh once they have spoken" in prompt
    # still there once, in the reference, where the doctor can draw on it
    assert prompt.count("Check mood") == 1
    assert prompt.count("Worried about cancer") == 1


def test_the_management_ladder_fits_a_station_with_no_drug_to_prescribe() -> None:
    """A Parkinson's station is exam, bloods and referral. The ladder used to have a
    rung that only a prescription could climb, so the model skipped the ladder and
    read the investigation list out in one turn."""
    prompt = AthenaDoctorFormatter.create_prompt("Hypothyroidism", {"patient_biodata": "Jane, 44"}, PLAN)
    assert "the name of the treatment and what it is for" not in prompt
    assert "a tablet, a test, a referral" in prompt
    assert "Never open this phase with what you are going to do" in prompt
    assert "six trips through 3 and 4" in prompt


def test_a_condition_the_patient_names_has_to_be_answered_in_their_word() -> None:
    """She said "Parkinson's", her father had it, and the doctor talked around the word
    for three turns. The ban it obeyed lived in the red-flag step, not the earned rule."""
    prompt = AthenaDoctorFormatter.create_prompt("Hypothyroidism", {"patient_biodata": "Jane, 44"}, PLAN)
    assert "Never name the disease you are screening for unless" not in prompt
    assert "once the patient" in prompt and "has named it themselves, it lets you, in their word" in prompt
    assert "Reaching the end without ever having said their word back to them is a breach" in prompt
    # and it is answered where the diagnosis belongs, not handed out mid-history
    assert "In the history, do not answer it yet" in prompt


def test_the_doctor_is_told_that_finishing_the_list_is_not_finishing() -> None:
    prompt = AthenaDoctorFormatter.create_prompt("Hypothyroidism", {"patient_biodata": "Jane, 44"}, PLAN)
    assert "Finishing the list is not finishing the consultation" in prompt
    assert "Closing early is a failure here, not efficiency" in prompt
    # no hard number: a rendered duration here would vary by framework and would
    # also invite padding to reach it
    assert "do not close before" not in prompt.lower()
