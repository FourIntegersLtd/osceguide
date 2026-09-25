from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class RecordArrival(BaseModel):
    """Public: a visitor landing from a partner link, before any account exists."""

    partner: str = Field(min_length=1, max_length=32)
    visitor_key: str = Field(min_length=1, max_length=64)
    ref_id: str | None = None
    landing_path: str | None = Field(default=None, max_length=300)
    utm: dict[str, str] = Field(default_factory=dict)


class ArrivalRecorded(BaseModel):
    id: uuid.UUID
    partner: str
    exam_code: str | None


class TrackingReference(BaseModel):
    """What a partner puts in one link, and where that link points."""

    exam_code: str
    ref_id: str
    landing_path: str


class FunnelRead(BaseModel):
    partner: str
    arrivals: int
    signups: int
    purchases: int
    signup_rate: float
    purchase_rate: float


class ReferralRead(BaseModel):
    code: str
    redeemed_count: int
    earned_pence: int


class AcquisitionRead(BaseModel):
    partner: str
    exam_code: str | None
    acquired_at: datetime


class RedeemReferral(BaseModel):
    code: str = Field(min_length=1, max_length=32)


class AddReporter(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class CreditSignup(BaseModel):
    """Ties the signed-in account to the visit that brought them.

    Sent after registering, with the key the arrival was logged under; the
    browser holds it and the backend never sees a partner cookie.
    """

    visitor_key: str = Field(min_length=1, max_length=64)


class ReferralAdminRead(BaseModel):
    """One referral, as the person settling it needs to see it.

    Emails rather than ids: a uuid is not on a bank statement.
    """

    id: uuid.UUID
    code: str
    referrer_email: str
    referred_email: str | None
    redeemed_at: datetime | None
    earned_pence: int
    payout_status: str
    paid_at: datetime | None
    payout_reference: str | None


class SetReferralPayout(BaseModel):
    payout_status: str = Field(pattern="^(unpaid|paid)$")
    payout_reference: str | None = Field(default=None, max_length=64)
