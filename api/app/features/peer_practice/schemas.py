from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.core.audience import AudienceIn, AudienceOut
from app.features.attempts.schemas_material import (
    CandidateScenarioRead, DoctorInformationRead, ManagementPlanRead, StationTeachingRead,
)
from app.features.attempts.schemas_roleplay import PatientRoleplayRead


class JoinQueue(BaseModel):
    exam_code: str = Field(min_length=1, max_length=32)
    # Which room to wait in: everyone, your institution, or one teaching group.
    # You hold one place at a time, so asking for a different room while
    # already waiting returns the place you have.
    audience: AudienceIn = Field(default_factory=AudienceIn)


class QueueStatus(BaseModel):
    """Where someone stands, and what to do next.

    `position` is why this is one call: b2c polls a status endpoint every three
    seconds, and it should be able to answer "am I matched yet?" in one round
    trip.
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
    doctor_information: DoctorInformationRead | None = None
    patient_information: PatientRoleplayRead | None = None
    management: ManagementPlanRead | None = None
    scenario: CandidateScenarioRead | None = None
    teaching: StationTeachingRead | None = None


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
    station: PracticeStationRead | None = None
    partner_joined: bool = False


class SessionFeedback(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)
    would_practice_again: bool | None = None


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
