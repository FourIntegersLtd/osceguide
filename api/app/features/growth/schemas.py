"""What the growth routes accept and return."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.features.growth import domain


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


class AddReporter(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class CreditSignup(BaseModel):
    """Ties the signed-in account to the visit that brought them.

    Sent after registering, with the key the arrival was logged under; the
    browser holds it and the backend never sees a partner cookie.
    """

    visitor_key: str = Field(min_length=1, max_length=64)


class PayoutDetailsAdminRead(BaseModel):
    """A referrer's bank details, decrypted, as platform admin settlement needs them.

    Never returned to anyone but the person settling the payout — the account
    number is in full here, unlike `PayoutDetailsRead`.
    """

    bank_name: str
    account_holder_name: str
    sort_code: str
    account_number: str
    updated_at: datetime


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
    # None when the referrer has never saved bank details — settlement then
    # falls back to whatever channel it used before this existed.
    payout_details: PayoutDetailsAdminRead | None = None


class SetReferralPayout(BaseModel):
    payout_status: str = Field(pattern="^(unpaid|paid)$")
    payout_reference: str | None = Field(default=None, max_length=64)


# --- A1: a referrer's own bank details --------------------------------------


class PayoutDetailsRead(BaseModel):
    """A referrer's own bank details, as they see them on reload.

    The sort code only identifies a branch, not an account, so it is shown in
    full — matching how the retiring client redisplayed it. The account
    number stays masked to its last four digits.
    """

    bank_name: str
    account_holder_name: str
    sort_code: str
    account_number_last4: str
    updated_at: datetime


class PayoutDetailsWrite(BaseModel):
    """What a referrer submits to save or update their bank details.

    `account_number` is optional so someone can change their bank name
    without retyping a number that never left the client the first time
    around; the service keeps the previously stored number when this is
    omitted, and refuses with `payout_account_number_required` if none was
    ever stored.
    """

    bank_name: str = Field(min_length=1, max_length=200)
    account_holder_name: str = Field(min_length=1, max_length=200)
    # Accepts "12-34-56" or "123456" (the retiring client's own pattern);
    # normalised to six bare digits before it is encrypted.
    sort_code: str = Field(min_length=6, max_length=8)
    account_number: str | None = Field(default=None, min_length=6, max_length=10)

    @field_validator("sort_code")
    @classmethod
    def sort_code_is_well_formed(cls, sort_code: str) -> str:
        """Reject a malformed sort code here, at the door, rather than in the service."""
        try:
            domain.normalise_sort_code(sort_code)
        except domain.InvalidSortCode as exc:
            raise ValueError(str(exc)) from exc
        return sort_code

    @field_validator("account_number")
    @classmethod
    def account_number_is_well_formed(cls, account_number: str | None) -> str | None:
        """Reject a malformed account number here; `None` (omitted) passes through untouched."""
        if account_number is None:
            return None
        try:
            domain.validate_account_number(account_number)
        except domain.InvalidAccountNumber as exc:
            raise ValueError(str(exc)) from exc
        return account_number


# --- A2: a referrer's own referral history -----------------------------------


class ReferralHistoryRead(BaseModel):
    """One redeemed referral, as the person who issued the code reads their own history.

    `referee_email` is exposed here (unlike `ReferralAdminRead`'s two-sided
    view being admin-only): this row belongs to the caller, and the retiring
    client's history table names the referee in its "Referee Email" column.
    """

    id: uuid.UUID
    # The referral code that was redeemed to earn this row — this row's own
    # `code` column, e.g. "AB12CD34-EF5678", not the shareable code it was
    # generated from.
    code: str
    referee_email: str
    redeemed_at: datetime
    plan_code: str | None
    # Human label for `plan_code` ("3-Month Access"), or `None` when no plan
    # was recorded (an older or imported row).
    plan_label: str | None
    earned_pence: int
    payout_status: str
    paid_at: datetime | None


# Our arrival ledger against Mixpanel's landing events, for one partner and range.
class LandingReconciliationRead(BaseModel):
    partner: str
    exam_code: str | None = None
    utm_campaign: str | None = None
    # Inclusive UTC dates.
    from_date: date
    to_date: date
    ledger_raw_count: int
    mixpanel_raw_count: int | None = None
    # Ledger minus Mixpanel, and that as a percentage of the ledger. Null when
    # Mixpanel did not answer, or (the percentage) when the ledger is empty.
    delta: int | None = None
    delta_percent: float | None = None
    # `ok`, `mixpanel_unconfigured` or `mixpanel_error`.
    status: str
    mixpanel_error: str | None = None


# What a partner's clicks are estimated to have cost in a range, against what they brought in.
class PartnerSpendRead(BaseModel):
    partner: str
    from_date: date
    to_date: date
    estimated_click_count: int
    cost_per_click_pence: int
    estimated_spend_pence: int
    gross_revenue_pence: int
    net_margin_pence: int
    cost_per_acquisition_pence: int | None = None
    acquired_user_count: int
    click_count_source: str = domain.CLICK_COUNT_SOURCE
    billing_disclaimer: str = domain.SPEND_BILLING_DISCLAIMER
    currency: str = "gbp"


# A partner pilot's cost per click and spend alert settings.
class PilotConfigRead(BaseModel):
    partner: str
    cost_per_click_pence: int
    spend_alert_thresholds_pence: list[int]
    # Empty means the platform's support address.
    spend_alert_recipients: list[str]
    last_alerted_threshold_pence: int


class UpdatePilotConfig(BaseModel):
    """Change a pilot's rate or its alerts. Fields left out are unchanged.

    `reset_spend_alerts` forgets which thresholds have already alerted, so
    raised or lowered thresholds are judged afresh.
    """

    cost_per_click_pence: int | None = Field(default=None, ge=0)
    spend_alert_thresholds_pence: list[int] | None = Field(default=None, max_length=20)
    spend_alert_recipients: list[EmailStr] | None = Field(default=None, max_length=20)
    reset_spend_alerts: bool = False
