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
