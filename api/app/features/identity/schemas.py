"""The public shape of identity. Declared here, mapped in the service."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class MembershipRead(BaseModel):
    org_id: uuid.UUID
    org_slug: str
    # Optional because the lookup that fills it is a display concern: a
    # membership authorises with its slug and role alone.
    org_name: str | None = None
    # What the organisation is for: "institution" or "partner". The frontend
    # chooses which workspace shell to render from this, so a partner sees
    # their funnel where an institution sees its cohort.
    org_type: str | None = None
    role: str
    surface: str | None = None


class UserRead(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    is_platform_admin: bool
    must_change_password: bool
    memberships: list[MembershipRead] = Field(default_factory=list)
    active_org_slug: str | None = None
    last_login_at: datetime | None = None
    # When they sit the real thing. The consumer dashboard counts down to it,
    # and both fields are on `/me` because every screen that needs them
    # already reads it. `exam_time` is optional even when `exam_date` is set —
    # a date alone is enough for the countdown.
    exam_date: date | None = None
    exam_time: time | None = None
    # Whether the two custom timers below apply. Off leaves whatever durations
    # are saved unused, matching the retiring client's "Extra reading time"
    # checkbox.
    needs_extra_time: bool = False
    # Custom reading-phase and simulation-phase timer durations, in seconds.
    # Replaces `extra_reading_percent` on this surface (A3); each is
    # independently optional.
    custom_reading_seconds: int | None = None
    custom_simulation_seconds: int | None = None
    # Which exam this account is for, chosen at sign-up. A preference, not a
    # grant: what somebody may open is decided by their entitlements, not this
    # field. `GET /me/dashboard` is what turns it into an exam somebody can use.
    exam_code: str | None = None
    ai_training_consent: bool = False
    colleague_waiting_email: bool = False
    replay_onboarding: bool = False


# A timer of zero is not a custom timer at all; 3659 is 60 minutes 59 seconds,
# the retiring client's own ceiling (`TimerSettingsModal`: minutes 0-60,
# seconds 0-59).
CUSTOM_TIMER_MIN_SECONDS = 1
CUSTOM_TIMER_MAX_SECONDS = 3659


class UpdateMe(BaseModel):
    """What a person may change about themselves. Absent means "leave it"."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    exam_date: date | None = None
    # Sent as an explicit `null` to clear; see `fields_sent` in `service.update_me`.
    exam_time: time | None = None
    needs_extra_time: bool | None = None
    custom_reading_seconds: int | None = Field(
        default=None, ge=CUSTOM_TIMER_MIN_SECONDS, le=CUSTOM_TIMER_MAX_SECONDS
    )
    custom_simulation_seconds: int | None = Field(
        default=None, ge=CUSTOM_TIMER_MIN_SECONDS, le=CUSTOM_TIMER_MAX_SECONDS
    )
    # Settable once, by an account with no exam; refused as `exam_already_chosen` after that.
    exam_code: str | None = Field(default=None, min_length=1, max_length=32)
    ai_training_consent: bool | None = None
    colleague_waiting_email: bool | None = None
    replay_onboarding: bool | None = None


class CloseAccount(BaseModel):
    """Confirm closing the account. A password when one is set, otherwise the word delete."""

    password: str | None = None
    confirm: str | None = None


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 - a scheme name, not a secret
    expires_in: int


class AuthResult(TokenPair):
    user: UserRead


class StreamTicket(BaseModel):
    """A short-lived credential for one `EventSource` connection.

    `EventSource` cannot send an `Authorization` header; see `core.streams` for
    why this exists rather than a cookie or a token in the query string.
    """

    ticket: str
    expires_in: int


class RegisterRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1, max_length=512)
    # Which exam they came to sit. The per-exam landing pages carry it into the
    # form, which is how the retiring client's per-exam subdomains are replaced
    # on one domain. Optional, because an institution's member registers
    # without one and gets their exams from the organisation.
    exam_code: str | None = Field(default=None, min_length=1, max_length=32)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=512)


class LegacyExchangeRequest(BaseModel):
    """Trade a token one of the legacy backends issued for a platform pair.

    `provider` is a closed set rather than a string because it selects the
    secret the token is verified against; an open one would let the caller
    choose its own key.
    """

    provider: Literal["consumer", "institution"]
    token: str = Field(min_length=1, max_length=4096)


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    """The session to end.

    Optional: without it every session ends, which is what "sign me out
    everywhere" means. With it only the presented chain goes, so signing out on
    a phone leaves the laptop signed in.
    """

    refresh_token: str | None = None


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    password: str = Field(min_length=1, max_length=512)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=512)
    new_password: str = Field(min_length=1, max_length=512)


class Accepted(BaseModel):
    """Returned where the answer must not depend on whether a record exists."""

    status: str = "accepted"


# --- The personal data export (E-5): `GET /me/export`.


class ExportedTranscriptMessage(BaseModel):
    """One spoken turn, as the export hands it back."""

    role: str
    message: str
    spoken_at: datetime


class ExportedTranscript(BaseModel):
    """One attempt's delivery record and the turns it carries."""

    complete: bool
    messages: list[ExportedTranscriptMessage] = Field(default_factory=list)


class ExportedResult(BaseModel):
    """One mark the engine produced for an attempt."""

    framework_id: str
    policy_version: str
    payload: dict[str, object]
    scored_at: datetime


class ExportedAttempt(BaseModel):
    """One attempt this person ran, with its own transcript and marks."""

    id: uuid.UUID
    kind: str
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    transcript: ExportedTranscript
    results: list[ExportedResult] = Field(default_factory=list)


class ExportedPayment(BaseModel):
    """One payment this person made."""

    receipt_id: str | None = None
    amount_total_pence: int
    amount_tax_pence: int
    currency: str
    receipt_url: str | None = None
    paid_at: datetime


class ExportedProfile(BaseModel):
    """The account fields the export carries about the person themselves."""

    id: uuid.UUID
    email: str
    name: str
    exam_code: str | None = None
    exam_date: date | None = None
    created_at: datetime


class MyDataExport(BaseModel):
    """Everything `GET /me/export` hands back: one person's own data."""

    profile: ExportedProfile
    attempts: list[ExportedAttempt] = Field(default_factory=list)
    payments: list[ExportedPayment] = Field(default_factory=list)
