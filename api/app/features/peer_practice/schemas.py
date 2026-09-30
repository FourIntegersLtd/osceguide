"""The shapes peer practice sends and receives: the queue, the session, its station and feedback."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.core.audience import AudienceIn, AudienceOut
from app.core.schemas import AudienceSectionRead


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
    """A peer session's station, for whichever of the two humans is asking.

    `sections` are the template's audience sections this viewer's role and
    phase may see, in template order — the same `AudienceSectionRead` shape
    `stations` defines once, projected by `service_station._station_payload`:
    the candidate audience always, the patient audience (with its `hidden`
    blocks, the actor's own script) for whoever is not the doctor or once the
    debrief has revealed it, and the examiner audience only once revealed.
    """

    station_id: uuid.UUID
    station_version_id: uuid.UUID
    title: str
    sections: list[AudienceSectionRead] = Field(default_factory=list)


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
