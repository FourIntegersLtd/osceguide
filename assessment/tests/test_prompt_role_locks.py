"""Every live persona says whose lines it speaks, in its opening instructions.

The drift these guard against is specific: a simulated patient that starts
asking clinical questions, an examiner that starts teaching, a tutor that
climbs back into the consultation it is reviewing. Each of those was possible
because the prompt never said which side of the conversation the model was on.

A per-turn reminder was tried alongside this and measured away: it bought
nothing on the patient and made the consulting doctor worse. The prompt is
where the role lives, which is what these guard.

These are content tests. They assert the property that matters rather than the
wording, so a prompt can be rewritten without editing them, but it cannot be
rewritten into one that forgets to cast the model.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from osce_assessment.prompts import (
    DEBRIEF_GREETING,
    EXAMINER_GREETINGS,
    PATIENT_GREETINGS,
    AthenaDoctorFormatter,
    DashboardTutorFormatter,
    DebriefPromptFormatter,
    create_station_prompt,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _station(name: str) -> dict:
    return json.loads((FIXTURES / "stations" / f"{name}.json").read_text())


def _untemplated_patient() -> str:
    """A station with no template: block ids matched by their common spellings."""
    return create_station_prompt(_station("untemplated_station"))


def _templated_patient() -> str:
    station = _station("templated_station")
    return create_station_prompt(station, station["layout"])


def _examiner() -> str:
    station = _station("templated_station")
    return create_station_prompt(station, station["layout"], persona="examiner")


def _doctor() -> str:
    return AthenaDoctorFormatter.create_prompt("Hypothyroidism", {"patient_biodata": "Jane, 44"}, {"explanation": "x"})


def _tutor() -> str:
    return DebriefPromptFormatter.create_prompt(transcript="## Doctor [ID:msg_0]\nHello", management_plan="## Explanation\nx")


def _remembering_tutor() -> str:
    return DashboardTutorFormatter.create_prompt({"consultations": [{"title": "Hip pain", "days_ago": 2}]})


LIVE_PROMPTS = {
    "untemplated patient": (_untemplated_patient, "You are the patient", "speaking to you is the doctor"),
    "templated patient": (_templated_patient, "You are the patient", "speaking to you is the doctor"),
    "examiner": (_examiner, "You are the examiner", "speaking to you is the candidate"),
    "consulting doctor": (_doctor, "You are the doctor", "speaking to you is the patient"),
    "debrief tutor": (_tutor, "You are the tutor", "speaking to you is the doctor"),
    "remembering tutor": (_remembering_tutor, "You are this doctor's regular tutor", "speaking to you is the doctor"),
}


@pytest.mark.parametrize(("name", "spec"), LIVE_PROMPTS.items(), ids=list(LIVE_PROMPTS))
def test_every_live_persona_names_its_role_and_its_counterpart(name, spec) -> None:
    render, persona, counterpart = spec
    prompt = render()
    assert prompt.startswith("<role>"), f"{name}: the role is not the first thing the model reads"
    assert persona in prompt, name
    assert counterpart in prompt, name
    assert "You must never:" in prompt, name


@pytest.mark.parametrize(("name", "spec"), LIVE_PROMPTS.items(), ids=list(LIVE_PROMPTS))
def test_every_live_persona_is_told_it_is_being_spoken_aloud(name, spec) -> None:
    assert "<speech>" in spec[0](), name


def test_the_patient_is_forbidden_the_clinician_behaviours_that_actually_happen() -> None:
    for prompt in (_untemplated_patient(), _templated_patient()):
        assert "offer a diagnosis" in prompt
        assert "examine anyone" in prompt
        assert "safety-net, summarise the consultation" in prompt


def test_the_examiner_is_forbidden_to_teach_or_answer_itself() -> None:
    prompt = _examiner()
    assert "answer your own question" in prompt
    assert "teach, hint, prompt, or give away any part of the expected answer" in prompt


def test_the_doctor_may_not_raise_what_the_patient_has_not_said() -> None:
    """The reported break: the doctor asked a mother what she had noticed about her baby's leg.

    She had given it a name and an age and nothing else. The prompt hands the
    model the whole station — diagnosis, records, management plan — so without
    this rule it consults from the file rather than from the conversation.
    """
    prompt = _doctor()
    assert "<earned_information_rule>" in prompt
    assert "they said it in this conversation" in prompt
    assert "The working diagnosis and the management plan never qualify" in prompt
    assert "raise a symptom, a body part, a person, a timeline or a worry" in prompt


def test_the_doctors_first_history_question_is_not_built_from_the_case_file() -> None:
    prompt = _doctor()
    opening = prompt[prompt.index("a. Presenting complaint"):prompt.index("b. Red flags")]
    assert "assumes nothing" in opening
    assert "until the patient has named the problem themselves" in opening
    assert "never the source of your first question" in opening
    # the complaint is explored before it is left, not sampled with four questions
    assert "fewer than eight" in opening


def test_the_tutor_is_told_it_was_not_in_the_consultation() -> None:
    prompt = _tutor()
    assert "re-enact the consultation" in prompt
    assert "speak as the patient or as the doctor from the transcript" in prompt


def test_the_diagnosis_is_fenced_off_rather_than_announced() -> None:
    """It used to be the first heading, which invites reasoning about the case instead of living it.

    A station is named for its diagnosis, so the title is fenced for a patient
    persona however the station was authored.
    """
    prompt = _templated_patient()
    diagnosis = _station("templated_station")["title"]
    assert "<never_say>" in prompt
    assert prompt.index("<never_say>") < prompt.index(diagnosis)
    assert not prompt.startswith("# Diagnosis")


def test_the_examiner_is_told_the_station_rather_than_forbidden_it() -> None:
    """An examiner names the station; only the patient must not."""
    prompt = _examiner()
    assert "<station>" in prompt and "<never_say>" not in prompt


def test_hidden_material_is_not_volunteered() -> None:
    for prompt in (_untemplated_patient(), _templated_patient()):
        assert "<hidden_until_asked" in prompt
        assert "Never volunteer it." in prompt


# A patient does not run the encounter. These are the words that crept in when
# the greetings were written as a simulated-patient actor's lines: telling the
# doctor to begin, and knowing they are a case.
STAGE_DIRECTION = ("ready", "begin", "let's start", "shall we start", "say the word", "case")


@pytest.mark.parametrize("greeting", PATIENT_GREETINGS)
def test_a_patient_greeting_does_not_direct_the_consultation(greeting) -> None:
    lowered = greeting.lower()
    for phrase in STAGE_DIRECTION:
        assert phrase not in lowered, f"{greeting!r} stage-directs the doctor"


@pytest.mark.parametrize("greeting", PATIENT_GREETINGS)
def test_a_patient_greeting_is_short_and_hands_the_turn_over(greeting) -> None:
    """It is only a liveness cue: the presenting complaint waits for the doctor to ask."""
    assert len(greeting) <= 45, greeting
    assert "?" not in greeting, f"{greeting!r} asks the doctor a question"


def test_a_patient_greeting_never_receives_the_doctor() -> None:
    """One backend had the patient inviting the doctor in, which inverts the roles at word one."""
    for greeting in PATIENT_GREETINGS:
        assert "come in" not in greeting.lower()
        assert "expecting you" not in greeting.lower()


@pytest.mark.parametrize("greeting", EXAMINER_GREETINGS)
def test_an_examiner_greeting_introduces_the_examiner(greeting) -> None:
    """An examination does open with the examiner directing it, unlike a consultation."""
    assert "examin" in greeting.lower()


def test_the_debrief_greeting_asks_before_it_tells() -> None:
    assert DEBRIEF_GREETING.strip().endswith("?")


def test_the_examiner_is_not_told_to_do_what_it_is_forbidden_to_do() -> None:
    """The prompt forbade telling the candidate how they were doing, then told it to say "That's right".

    Models obeyed the nearer instruction and were then marked down for it, so the
    benchmark was partly measuring a contradiction rather than the models.
    """
    prompt = _examiner()
    assert "tell the candidate how they are doing" in prompt, "the rule itself must still be there"
    assert 'When they are right, say "Good"' not in prompt, "the contradicting instruction is back"
    assert "Acknowledge without marking" in prompt
