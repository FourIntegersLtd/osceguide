"""What a candidate may read about a station they are sitting, or have sat.

Split from `schemas.py` because these describe the *station* seen through an
attempt, while those describe the attempt itself. `service_material` is their
only producer.

The station document is one JSON blob whose shape differs per exam — SCA and
PLAB carry nested `doctor_information` / `management_plan` blocks, Ortho carries
flat candidate keys beside them. These shapes name the fields the screens
actually render and allow the rest through, so a station carrying more than any
of the four exams known today still reaches the browser intact. The alternative
— passing `content` straight out — would hand the candidate the patient's
persona and the examiner's expected answers.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class _Passthrough(BaseModel):
    """A block whose known fields are typed and whose unknown ones survive."""

    model_config = {"extra": "allow"}


class DoctorInformationRead(_Passthrough):
    """The candidate's brief: what the doctor has in front of them."""

    patient_biodata: str | None = None
    recent_notes: list[str] = Field(default_factory=list)
    current_medications: list[str] = Field(default_factory=list)
    past_medical_history: list[str] = Field(default_factory=list)
    recent_investigations: list[str] = Field(default_factory=list)
    social_history: list[str] = Field(default_factory=list)
    photos: list[str] = Field(default_factory=list)
    doctor_task: str | None = None
    doctor_identity: str | None = None
    patient_information: list[str] = Field(default_factory=list)
    task_instructions: str | None = None


class PrioritisationPatientRead(_Passthrough):
    """One patient on an Ortho prioritisation list."""

    number: int | None = None
    age: int | None = None
    gender: str | None = None


class CandidateScenarioRead(_Passthrough):
    """Candidate-facing keys that sit flat on the document rather than in a block.

    Ortho's stations are shaped this way: an interview or a trauma list rather
    than a consultation, so the brief is a scenario and a set of images.
    """

    station_type: str | None = None
    clinical_scenario_title: str | None = None
    clinical_scenario: str | None = None
    radiograph_image_url: str | None = None
    additional_image_urls: list[str] = Field(default_factory=list)
    background_overview: str | None = None
    patient_list_for_candidate: list[PrioritisationPatientRead] = Field(default_factory=list)
    duration_minutes: int | None = None


class PatientIdentityRead(BaseModel):
    """Who the candidate is about to speak to, for the consultation header."""

    name_line: str | None = None
    gender: str | None = None


class AttemptBriefRead(BaseModel):
    """The reading-time screen, keyed on the attempt rather than the station.

    On the attempt because that is what the entitlement check has already been
    made against: `LibraryStationRead` deliberately carries no content, since
    the library is browsable by everyone and the brief is part of the exam.
    Once somebody has started a station, the brief is theirs to read.
    """

    attempt_id: uuid.UUID
    kind: str
    status: str
    exam_code: str
    station_id: uuid.UUID
    station_version_id: uuid.UUID
    station_title: str
    set_entry_id: uuid.UUID | None = None
    patient: PatientIdentityRead
    doctor_information: DoctorInformationRead | None = None
    scenario: CandidateScenarioRead | None = None


class PatientReviewRead(BaseModel):
    """The patient's side, as a candidate may read it afterwards.

    Not a passthrough: `persona`, `opening_sentence`, `expanded_history` and
    the hidden question list are how the patient is played, and they stay on
    the server. What is here is what the old management screen showed — the
    biodata line and the ideas, concerns and expectations the candidate was
    supposed to draw out.
    """

    patient_biodata: str | None = None
    gender: str | None = None
    idea: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    expectation: list[str] = Field(default_factory=list)


class ManagementPlanRead(_Passthrough):
    """The model answer, readable once the consultation is over."""

    explanation: str | None = None
    differential_diagnosis: list[str] = Field(default_factory=list)
    examination_findings: list[str] = Field(default_factory=list)
    assessment: list[str] = Field(default_factory=list)
    further_investigations: list[str] = Field(default_factory=list)
    social_concerns: list[str] = Field(default_factory=list)
    ice: list[str] = Field(default_factory=list)
    immediate_actions: list[str] = Field(default_factory=list)
    pharmacological_treatment: list[str] = Field(default_factory=list)
    non_pharmacological_treatment: list[str] = Field(default_factory=list)
    health_education: list[str] = Field(default_factory=list)
    follow_up: str | None = None
    safety_netting: str | None = None
    additional_notes: str | None = None


class InterviewQuestionRead(_Passthrough):
    question: str | None = None
    answer: str | None = None


class StationTeachingRead(_Passthrough):
    """Ortho's flat teaching keys: the debrief material for a non-consultation station."""

    key_concerns: list[str] = Field(default_factory=list)
    history_overview: str | None = None
    examination_overview: str | None = None
    investigations_overview: str | None = None
    management_overview: str | None = None
    interview_questions: list[InterviewQuestionRead] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    examiner_additional_info: list[PrioritisationPatientRead] = Field(default_factory=list)
    suggested_order_overview: str | None = None
    suggested_order: dict[str, Any] | None = None
    communication_themes: list[str] = Field(default_factory=list)
    consent_approach: str | None = None
    breaking_bad_news_framework: str | None = None
    professional_conduct_topics: list[str] = Field(default_factory=list)
    key_learning_points: list[str] = Field(default_factory=list)
    portfolio_themes: list[str] = Field(default_factory=list)


class AttemptReviewRead(BaseModel):
    """The management step: what the candidate should have covered."""

    attempt_id: uuid.UUID
    kind: str
    status: str
    exam_code: str
    station_id: uuid.UUID
    station_version_id: uuid.UUID
    station_title: str
    set_entry_id: uuid.UUID | None = None
    patient_information: PatientReviewRead | None = None
    management_plan: ManagementPlanRead | None = None
    scenario: CandidateScenarioRead | None = None
    teaching: StationTeachingRead | None = None


class AttemptHistoryItem(BaseModel):
    """One row of "what have I sat", with its station named.

    `has_result` rather than a status the client has to interpret: "is there
    feedback to open" is the only question every screen listing these asks.
    """

    id: uuid.UUID
    kind: str
    status: str
    exam_code: str
    station_id: uuid.UUID | None = None
    station_version_id: uuid.UUID | None = None
    station_title: str | None = None
    set_entry_id: uuid.UUID | None = None
    created_at: datetime
    completed_at: datetime | None = None
    has_result: bool = False
