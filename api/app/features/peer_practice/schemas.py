"""The shapes peer practice sends and receives: the queue, the session, its station and feedback."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.core.audience import AudienceIn, AudienceOut


class _Passthrough(BaseModel):
    """A block whose known fields are typed and whose unknown ones survive.

    These mirror the attempt material shapes but are peer practice's own, and
    the `Practice` prefix is what keeps their OpenAPI component names distinct:
    two models sharing a name makes FastAPI qualify *both*, which renames the
    attempt types the web client already imports.
    """

    model_config = {"extra": "allow"}


class PracticeDoctorInformationRead(_Passthrough):
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


class PracticeCandidateScenarioRead(_Passthrough):
    station_type: str | None = None
    clinical_scenario_title: str | None = None
    clinical_scenario: str | None = None
    radiograph_image_url: str | None = None
    additional_image_urls: list[str] = Field(default_factory=list)
    background_overview: str | None = None
    duration_minutes: int | None = None


class PracticeManagementPlanRead(_Passthrough):
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


class PracticeStationTeachingRead(_Passthrough):
    key_concerns: list[str] = Field(default_factory=list)
    history_overview: str | None = None
    examination_overview: str | None = None
    investigations_overview: str | None = None
    management_overview: str | None = None
    references: list[str] = Field(default_factory=list)
    suggested_order_overview: str | None = None
    suggested_order: dict[str, Any] | None = None
    communication_themes: list[str] = Field(default_factory=list)
    consent_approach: str | None = None
    breaking_bad_news_framework: str | None = None
    professional_conduct_topics: list[str] = Field(default_factory=list)
    key_learning_points: list[str] = Field(default_factory=list)
    portfolio_themes: list[str] = Field(default_factory=list)


class PracticePatientRoleplayRead(BaseModel):
    patient_biodata: str | None = None
    gender: str | None = None
    idea: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    expectation: list[str] = Field(default_factory=list)
    opening_sentence: str | None = None
    expanded_history: str | None = None
    persona: str | None = None
    family_social_history: list[str] = Field(default_factory=list)
    past_med_history_allergies: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)


class JoinQueue(BaseModel):
    exam_code: str = Field(min_length=1, max_length=32)
    # Which room to wait in: everyone, your institution, or one teaching group.
    # You hold one place at a time, so asking for a different room while
    # already waiting returns the place you have.
    audience: AudienceIn = Field(default_factory=AudienceIn)


class QueueStatus(BaseModel):
    """Where someone stands, and what to do next.

    `position` is why this is one call: a polling client should be able to
    answer "am I matched yet?" in one round trip.
    """

    entry_id: uuid.UUID
    status: str
    position: int | None = None
    waiting_count: int = 0
    session_id: uuid.UUID | None = None
    audience: AudienceOut


class PracticeStationRead(BaseModel):
    station_id: uuid.UUID
    station_version_id: uuid.UUID
    title: str
    reading_brief: str | None = None
    patient_script: str | None = None
    management_plan: str | None = None
    doctor_information: PracticeDoctorInformationRead | None = None
    patient_information: PracticePatientRoleplayRead | None = None
    management: PracticeManagementPlanRead | None = None
    scenario: PracticeCandidateScenarioRead | None = None
    teaching: PracticeStationTeachingRead | None = None


class PracticeSessionRead(BaseModel):
    id: uuid.UUID
    exam_code: str
    my_role: str
    partner_user_id: uuid.UUID
    room_name: str | None
    status: str
    current_phase: str | None = None
    phase_ends_at: datetime | None = None
    preparation_started_at: datetime | None = None
    doctor_joined_at: datetime | None = None
    patient_joined_at: datetime | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    end_reason: str | None = None
    station: PracticeStationRead | None = None
    partner_joined: bool = False
    # The doctor's marked attempt, and where it has got to. Only the doctor is
    # scored — the rubric is written for the doctor's performance — so the
    # patient always reads `none` and never sees somebody else's attempt id.
    doctor_attempt_id: uuid.UUID | None = None
    feedback_state: str = "none"
    # The accept handshake. `accept_expires_at` is only set while `status` is
    # `pending_accept`; `my_accepted`/`partner_accepted` read the two acceptance
    # columns from whichever side the viewer is. `requeued_entry_id` is the
    # viewer's own new queue place, set only when this pairing ended by a
    # decline or a timeout and the viewer had already accepted it.
    accept_expires_at: datetime | None = None
    my_accepted: bool = False
    partner_accepted: bool = False
    requeued_entry_id: uuid.UUID | None = None


class SessionFeedback(BaseModel):
    """What one participant leaves after a session, matching what the legacy form asked for.

    `would_practice_again` is the one field the legacy form always required —
    a session either felt worth repeating or it did not, and that answer is
    what a good-match signal is built from. The star rating was always
    optional there, which this keeps: someone declining to rate a partner is
    not the same as having nothing to say about practising with them again.
    """

    would_practice_again: bool
    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=500)


class ReportAbuse(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ReportNoShow(BaseModel):
    message: str | None = Field(default=None, max_length=500)


class EndSession(BaseModel):
    reason: str | None = Field(default=None, max_length=32)


class RoomGrant(BaseModel):
    """What a browser needs to join a peer session's room.

    This slice's own shape rather than `voice`'s or `sittings`', for the
    reason those two do not share one either: a wire contract belongs to the
    routes that serve it.
    """

    token: str
    server_url: str
    room: str
