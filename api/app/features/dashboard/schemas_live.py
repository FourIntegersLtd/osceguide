"""The exam-day board: every examination this organisation has running, at once.

Every number here is computed server-side, against the server's clock, because this is
the screen somebody makes decisions from and a browser with a wrong system time should
not be one of the inputs.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class LivePerson(BaseModel):
    user_id: uuid.UUID
    name: str | None = None
    email: str | None = None


class LiveStation(BaseModel):
    """The station a candidate is on now. Null when the circuit is on a break."""

    slot_id: uuid.UUID
    slot_index: int
    title: str | None = None


class LiveCircuit(BaseModel):
    """One examination in progress, as a row on the board."""

    circuit_id: uuid.UUID
    circuit_name: str
    sitting_id: uuid.UUID
    sitting_name: str
    mode: str
    room_name: str | None
    supervisor: LivePerson | None = None
    # Every candidate on the circuit: one in an exam, the whole group in
    # training. Named rather than counted, because the board's job is to let
    # somebody find a person.
    candidates: list[LivePerson] = Field(default_factory=list)
    current_station: LiveStation | None = None

    phase: str | None = None
    phase_started_at: datetime | None = None
    phase_ends_at: datetime | None = None
    paused: bool = False
    auto_advance: bool = True
    # Time in this phase and time left in it, both excluding any pause.
    elapsed_seconds: int | None = None
    remaining_seconds: int | None = None
    # How far past its end the phase has run; null while it is not late.
    overdue_seconds: int | None = None

    stations_total: int
    stations_completed: int

    # The recording of the station in progress, so a station running with
    # nothing recording it is visible rather than discovered afterwards.
    attempt_id: uuid.UUID | None = None
    attempt_status: str | None = None
    # Stable codes, never sentences: the board decides how to say it.
    alerts: list[str] = Field(default_factory=list)


class LiveBoard(BaseModel):
    """Everything running in one organisation, in one request.

    `as_of` is the server time the numbers were computed against, so a client
    can count down from the deadlines rather than waiting to be told again.
    """

    as_of: datetime
    circuits: list[LiveCircuit] = Field(default_factory=list)
    # False when no job worker has checked in lately. The api still advances due
    # circuits on this read, but webhooks, marking and patient removal wait for it.
    worker_running: bool = True


class LiveRunRead(BaseModel):
    """One circuit run that has finished, as the board last saw it.

    Field names follow `LiveCircuit`. `status` is `completed` when every
    station was sat and `ended_early` when any was skipped.
    """

    id: uuid.UUID
    circuit_id: uuid.UUID | None
    circuit_name: str
    sitting_id: uuid.UUID | None
    sitting_name: str
    mode: str
    supervisor: LivePerson | None = None
    started_at: datetime | None
    ended_at: datetime
    candidate_count: int
    stations_total: int
    stations_completed: int
    status: str
