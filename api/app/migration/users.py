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
from datetime import UTC, datetime
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

        legacy_id = str(record.get("id") or record.get("user_id") or "").strip()
        if legacy_id:
            user.legacy_ids.add(legacy_id)

        if email in admins:
            user.is_platform_admin = True

        product = str(record.get("app_type") or "").strip().lower()
        if product:
            user.legacy_products.add(product)

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
