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
    consumer_role: str = "user"


@dataclass(frozen=True)
class MergedLegacyPayment:
    email: str
    exam_code: str
    plan_code: str
    paid_at: datetime
    stripe_payment_intent_id: str
    amount_pence: int = 0


@dataclass(frozen=True)
class MergedReferral:
    email: str
    code: str
    earned_pence: int


@dataclass(frozen=True)
class MergedEntitlement:
    email: str
    exam_code: str
    source: str
    starts_at: datetime | None
    ends_at: datetime | None


def normalize_email(raw: Any) -> str:
    return str(raw or "").strip().lower()


def parse_timestamp(raw: Any) -> datetime | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def parse_date(raw: Any) -> date | None:
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
    accessibility = record.get("accessibility")
    if not isinstance(accessibility, dict):
        return 0
    if accessibility.get("needs_extra_reading_time"):
        return 25
    return 0


def exam_for_product(app_type: Any) -> str:
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
    admins = {normalize_email(a) for a in admin_emails}
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
