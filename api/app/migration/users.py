"""Merging legacy user records into one person.

A consumer exists as up to four Firestore documents — one per product, each with
its own `has_paid` and `plan_end_date` — and may also have a `b2b_users` row.
The merge key is the lowercased email, which is why `users.email` is `citext`
and unique: the database enforces what this assumes.

Pure functions, so the migration can be argued about and tested before anyone
points it at production data.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

# Oracle: `osce_assessment.compat.legacy_app_types`. The last place this mapping
# exists; after the migration the shim is deleted.
LEGACY_PRODUCT_TO_EXAM = {
    "sca": "sca",
    "plab": "plab",
    "casc": "casc",
    "ortho": "ortho",
}


class UnknownLegacyProduct(ValueError):
    """An `app_type` with no exam.

    Refused rather than defaulted. b2c falls back to SCA, which is how CASC
    transcripts came to be marked with a GP rubric; an import is exactly the
    wrong place to repeat that.
    """


class UnusableRecord(ValueError):
    """A record that cannot be imported. Reported, never silently dropped."""


@dataclass
class MergedUser:
    """One person, folded together from every legacy document that mentions them."""

    email: str
    name: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    is_platform_admin: bool = False
    # Neither legacy hash is argon2, and b2b's is unsalted SHA-256. Importing
    # either would mean carrying a weak credential forward, so nobody's
    # password comes across and everybody resets.
    password_hash: str | None = None
    must_reset_password: bool = True
    legacy_products: set[str] = field(default_factory=set)
    # Every legacy document id that turned out to be this person. A transcript
    # names its author by Firestore document id, not by email, so without these
    # there is no way to attach imported attempts to the user they belong to.
    legacy_ids: set[str] = field(default_factory=set)
    # Firestore document id per exam collection (`app_type` → `user_id`).
    legacy_ids_by_product: dict[str, str] = field(default_factory=dict)
    last_login_at: datetime | None = None
    exam_code: str | None = None
    exam_date: date | None = None
    extra_reading_percent: int = 0
    # A3's replacement for `extra_reading_percent` on the live API: the two
    # custom timer durations (seconds) and the gate that turns them on.
    # `extra_reading_percent` itself is left as-is above — this column stays
    # on `users` and nothing here changes how it is derived.
    needs_extra_time: bool = False
    custom_reading_seconds: int | None = None
    custom_simulation_seconds: int | None = None
    consumer_role: str = "user"
    # Legacy `inactive_engagement_email_sent_at`, carried across so the
    # engagement-email job (`identity.jobs.send_engagement_emails`) never
    # re-sends the "come try a station" nudge to someone legacy already
    # reached. Firestore holds this per app-type document, not per person, so
    # `merge_users` below keeps whichever is earliest across a person's docs —
    # the same "oldest wins" rule as `created_at`, since any one legacy send
    # already satisfies "never emailed before".
    engagement_email_sent_at: datetime | None = None


@dataclass(frozen=True)
class MergedLegacyPayment:
    """One legacy purchase, ready for `load_legacy_payments`."""

    email: str
    exam_code: str
    plan_code: str
    paid_at: datetime
    stripe_payment_intent_id: str
    amount_pence: int = 0


@dataclass(frozen=True)
class MergedReferral:
    """One legacy referral code and its earnings, ready for `load_legacy_referrals`."""

    email: str
    code: str
    earned_pence: int


@dataclass(frozen=True)
class MergedEntitlement:
    """One legacy grant of access to an exam, ready to become an `entitlements` row."""

    email: str
    exam_code: str
    source: str
    starts_at: datetime | None
    ends_at: datetime | None


def normalize_email(raw: Any) -> str:
    """An email address, stripped and lowercased so it matches the `citext` merge key."""
    return str(raw or "").strip().lower()


def parse_timestamp(raw: Any) -> datetime | None:
    """A legacy ISO timestamp as a UTC-aware `datetime`, or None if it is missing or unparseable."""
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def parse_date(raw: Any) -> date | None:
    """A legacy date, from a full timestamp or a bare `YYYY-MM-DD` string, or None if neither parses."""
    at = parse_timestamp(raw)
    if at is not None:
        return at.date()
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def extra_reading_from_record(record: dict[str, Any]) -> int:
    """The extra reading time percentage a legacy accessibility flag implies, or 0 if none applies."""
    accessibility = record.get("accessibility")
    if not isinstance(accessibility, dict):
        return 0
    if accessibility.get("needs_extra_reading_time"):
        return 25
    return 0


def _positive_int(raw: Any) -> int | None:
    """A legacy timer duration as a positive number of seconds, or None if it is missing,
    zero, or not a number — the legacy client never saved a timer of zero (A3)."""
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


@dataclass(frozen=True)
class AccessibilityTimers:
    """The A3 custom-timer fields a legacy `accessibility` block implies."""

    needs_extra_time: bool
    custom_reading_seconds: int | None
    custom_simulation_seconds: int | None


def accessibility_timers_from_record(record: dict[str, Any]) -> AccessibilityTimers:
    """Oracle: legacy `accessibility.needs_extra_reading_time`,
    `accessibility.doctor_timer_duration` and `accessibility.simulation_timer_duration`
    (`frontend/src/b2c/components/shared/ui/Timer.tsx`, `TimerSettingsModal.tsx`).

    The gate and the two durations are independent in the legacy data too:
    unticking the checkbox left the durations in place but stopped using
    them, so this reads all three rather than deriving one from another.
    """
    accessibility = record.get("accessibility")
    if not isinstance(accessibility, dict):
        return AccessibilityTimers(
            needs_extra_time=False, custom_reading_seconds=None, custom_simulation_seconds=None
        )
    return AccessibilityTimers(
        needs_extra_time=bool(accessibility.get("needs_extra_reading_time")),
        custom_reading_seconds=_positive_int(accessibility.get("doctor_timer_duration")),
        custom_simulation_seconds=_positive_int(accessibility.get("simulation_timer_duration")),
    )


def exam_for_product(app_type: Any) -> str:
    """The exam code for a legacy `app_type`, or `UnknownLegacyProduct` if none is mapped."""
    key = str(app_type or "").strip().lower()
    try:
        return LEGACY_PRODUCT_TO_EXAM[key]
    except KeyError as exc:
        raise UnknownLegacyProduct(
            f"No exam for legacy product {app_type!r}. Defaulting here would "
            "repeat the mistake that marks CASC with a GP rubric."
        ) from exc


def merge_users(
    b2c_users: Sequence[dict[str, Any]],
    *,
    b2b_users: Sequence[dict[str, Any]] = (),
    admin_emails: Iterable[str] = (),
) -> list[MergedUser]:
    """One row per person, from every record that mentions them."""
    admins = {normalize_email(admin_email) for admin_email in admin_emails}
    merged: dict[str, MergedUser] = {}

    for record in [*b2c_users, *b2b_users]:
        email = normalize_email(record.get("email"))
        if not email:
            raise UnusableRecord(f"A record has no email address and cannot be merged: {record!r}")

        user = merged.setdefault(email, MergedUser(email=email, created_at=datetime.now(UTC)))
        name = str(record.get("username") or record.get("name") or "").strip()
        if name and not user.name:
            user.name = name

        created = parse_timestamp(record.get("created_at"))
        if created and created < user.created_at:
            # Their account is as old as the first one they made. A new record
            # starts at `now()`, so the first real timestamp always wins.
            user.created_at = created

        doc_id = str(record.get("id") or "").strip()
        legacy_user_id = str(record.get("user_id") or "").strip()
        legacy_id = doc_id or legacy_user_id
        if legacy_id:
            user.legacy_ids.add(legacy_id)
        # Community and marketplace name authors by `user_id`, not the Firestore doc id.
        if legacy_user_id and legacy_user_id != doc_id:
            user.legacy_ids.add(legacy_user_id)

        if email in admins:
            user.is_platform_admin = True

        product = str(record.get("app_type") or "").strip().lower()
        if product:
            user.legacy_products.add(product)
            if legacy_id:
                user.legacy_ids_by_product[product] = legacy_id

        login = parse_timestamp(record.get("last_login"))
        if login and (user.last_login_at is None or login > user.last_login_at):
            user.last_login_at = login

        reading = extra_reading_from_record(record)
        if reading > user.extra_reading_percent:
            user.extra_reading_percent = reading

        timers = accessibility_timers_from_record(record)
        if timers.needs_extra_time:
            user.needs_extra_time = True
        if timers.custom_reading_seconds is not None and user.custom_reading_seconds is None:
            user.custom_reading_seconds = timers.custom_reading_seconds
        if timers.custom_simulation_seconds is not None and user.custom_simulation_seconds is None:
            user.custom_simulation_seconds = timers.custom_simulation_seconds

        exam_on_record = parse_date(record.get("exam_date"))
        if exam_on_record and user.exam_date is None:
            user.exam_date = exam_on_record
            if product:
                user.exam_code = product

        role = str(record.get("role") or "").strip().lower()
        if role == "admin":
            user.consumer_role = "admin"

        if not user.exam_code and product:
            user.exam_code = product

        engagement_sent = parse_timestamp(record.get("inactive_engagement_email_sent_at"))
        if engagement_sent and (
            user.engagement_email_sent_at is None or engagement_sent < user.engagement_email_sent_at
        ):
            user.engagement_email_sent_at = engagement_sent

    return list(merged.values())


def entitlements_for(record: dict[str, Any]) -> list[MergedEntitlement]:
    """What a legacy user document says somebody paid for.

    Expired grants come across too. "Your access ended in March" is a better
    answer than an empty list, and the entitlement predicate already handles it.
    """
    email = normalize_email(record.get("email"))
    if not email:
        raise UnusableRecord("A record has no email address.")
    if not record.get("has_paid"):
        return []

    exam_code = exam_for_product(record.get("app_type"))
    return [
        MergedEntitlement(
            email=email,
            exam_code=exam_code,
            source="purchase",
            starts_at=parse_timestamp(record.get("plan_start_date")),
            ends_at=parse_timestamp(record.get("plan_end_date")),
        )
    ]


def legacy_payment_for(record: dict[str, Any]) -> MergedLegacyPayment | None:
    """The legacy payment a paid user record implies, or None if the record shows no payment."""
    if not record.get("has_paid"):
        return None
    email = normalize_email(record.get("email"))
    if not email:
        raise UnusableRecord("A record has no email address.")
    exam_code = exam_for_product(record.get("app_type"))
    plan_code = str(record.get("plan_type") or "one_month").strip()
    if not plan_code or plan_code == "no_plan":
        plan_code = "one_month"
    legacy_id = str(record.get("id") or record.get("user_id") or "unknown")
    product = str(record.get("app_type") or "sca")
    stripe_id = str(record.get("stripe_payment_intent_id") or "").strip()
    if not stripe_id:
        stripe_id = f"legacy-import:{product}:{legacy_id}"
    paid_at = parse_timestamp(record.get("plan_start_date")) or parse_timestamp(record.get("created_at"))
    if paid_at is None:
        paid_at = datetime.now(UTC)
    return MergedLegacyPayment(
        email=email,
        exam_code=exam_code,
        plan_code=plan_code,
        paid_at=paid_at,
        stripe_payment_intent_id=stripe_id,
    )


def referral_for(record: dict[str, Any]) -> MergedReferral | None:
    """The referral code and earnings a legacy user record carries, or None if it has none."""
    email = normalize_email(record.get("email"))
    if not email:
        return None
    referrals = record.get("referrals")
    if not isinstance(referrals, dict):
        return None
    code = str(referrals.get("referral_code") or "").strip()
    if not code:
        return None
    earned = referrals.get("referral_earnings")
    try:
        earned_pence = int(earned) if earned is not None else 0
    except (TypeError, ValueError):
        earned_pence = 0
    return MergedReferral(email=email, code=code, earned_pence=earned_pence)
