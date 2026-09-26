"""Transforms for B2C marketplace → `availability_posts` and `peer_sessions`."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.migration.legacy_ids import legacy_row_id
from app.migration.marketplace_time import scheduled_local_to_utc
from app.migration.users import UnknownLegacyProduct, exam_for_product, parse_timestamp


class MarketplaceTransformError(Exception):
    """A document that cannot become a marketplace post or session. Reported, never guessed at."""


def _starts_at(document: dict[str, Any]) -> datetime:
    """A post or session's start time, from `scheduled_at` or from a local date/time plus timezone."""
    at = parse_timestamp(document.get("scheduled_at"))
    if at is not None:
        return at
    date = str(document.get("scheduled_date") or "").strip()
    time = str(document.get("scheduled_time") or "").strip()
    if date and time:
        try:
            return scheduled_local_to_utc(date, time, str(document.get("timezone") or "UTC"))
        except ValueError as exc:
            raise MarketplaceTransformError(str(exc)) from exc
    raise MarketplaceTransformError("missing scheduled_at or scheduled_date/time")


@dataclass
class MigratedAvailabilityPost:
    """One legacy availability post, ready for `load_marketplace_posts`."""

    legacy_ref: str
    exam_code: str
    owner_legacy_user_id: str
    starts_at: datetime
    duration_minutes: int
    note: str | None
    status: str
    claimed_by_legacy_user_id: str | None = None
    claimed_at: datetime | None = None
    cancelled_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def row_id(self):
        """This post's deterministic primary key, derived from its legacy reference."""
        return legacy_row_id(self.legacy_ref)


@dataclass
class MigratedPeerSession:
    """One legacy peer practice session, ready for `load_peer_sessions`."""

    legacy_ref: str
    exam_code: str
    post_legacy_ref: str | None
    owner_legacy_user_id: str
    claimer_legacy_user_id: str
    starts_at: datetime
    status: str
    room_name: str | None = None
    ended_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def row_id(self):
        """This session's deterministic primary key, derived from its legacy reference."""
        return legacy_row_id(self.legacy_ref)

    @property
    def post_row_id(self):
        """The availability post this session was booked from, or None if it was not booked from one."""
        if self.post_legacy_ref is None:
            return None
        return legacy_row_id(self.post_legacy_ref)


def _exam(document: dict[str, Any]) -> str:
    """The exam a marketplace document belongs to, from its `app_type`."""
    product = str(document.get("app_type") or "").strip().lower()
    if not product:
        raise MarketplaceTransformError("document has no app_type")
    return exam_for_product(product)


def _map_post_status(raw: str | None) -> tuple[str, datetime | None]:
    """A legacy post status, mapped onto the platform's status set, plus a cancelled-at time if applicable."""
    status = str(raw or "available").strip().lower()
    if status in {"available", "claimed"}:
        return status, None
    if status in {"cancelled", "expired", "completed"}:
        return "cancelled", datetime.now(UTC)
    return "cancelled", None


def _map_session_status(raw: str | None) -> tuple[str, datetime | None]:
    """A legacy session status, mapped onto the platform's status set, plus an ended-at time if applicable."""
    status = str(raw or "scheduled").strip().lower()
    if status == "completed":
        return "completed", datetime.now(UTC)
    if status in {"cancelled", "no_show"}:
        return "cancelled", datetime.now(UTC)
    if status == "active":
        return "active", None
    if status == "scheduled":
        return "scheduled", None
    return "scheduled", None


def post_from_document(document: dict[str, Any]) -> MigratedAvailabilityPost:
    """Transform a `*_marketplace_posts` document into a `MigratedAvailabilityPost`."""
    try:
        exam_code = _exam(document)
    except UnknownLegacyProduct as exc:
        raise MarketplaceTransformError(str(exc)) from exc

    post_id = str(document.get("post_id") or document.get("id") or "").strip()
    if not post_id:
        raise MarketplaceTransformError("post has no post_id")

    owner_id = str(document.get("user_id") or "").strip()
    if not owner_id:
        raise MarketplaceTransformError(f"post {post_id} has no user_id")

    try:
        starts_at = _starts_at(document)
    except MarketplaceTransformError:
        raise MarketplaceTransformError(f"post {post_id} has no scheduled_at") from None

    status, cancelled_at = _map_post_status(document.get("status"))
    claimed_by = str(document.get("claimed_by_user_id") or "").strip() or None
    claimed_at = parse_timestamp(document.get("claimed_at"))
    if status == "claimed" and not claimed_by:
        claimed_by = str(document.get("claimer_user_id") or "").strip() or None

    note = str(document.get("note") or "").strip() or None
    created = parse_timestamp(document.get("created_at"))
    updated = created

    legacy_ref = f"{exam_code}:marketplace:post:{post_id}"
    warnings: list[str] = []
    if status == "claimed" and not claimed_by:
        warnings.append(f"post {post_id} is claimed but has no claimer user id")

    return MigratedAvailabilityPost(
        legacy_ref=legacy_ref,
        exam_code=exam_code,
        owner_legacy_user_id=owner_id,
        starts_at=starts_at,
        duration_minutes=30,
        note=note,
        status=status,
        claimed_by_legacy_user_id=claimed_by,
        claimed_at=claimed_at,
        cancelled_at=cancelled_at,
        created_at=created,
        updated_at=updated,
        warnings=warnings,
    )


def session_from_document(document: dict[str, Any]) -> MigratedPeerSession:
    """Transform a `*_marketplace_sessions` document into a `MigratedPeerSession`."""
    try:
        exam_code = _exam(document)
    except UnknownLegacyProduct as exc:
        raise MarketplaceTransformError(str(exc)) from exc

    session_id = str(document.get("session_id") or document.get("id") or "").strip()
    if not session_id:
        raise MarketplaceTransformError("session has no session_id")

    owner_id = str(document.get("poster_user_id") or document.get("user_id") or "").strip()
    claimer_id = str(document.get("claimer_user_id") or "").strip()
    if not owner_id or not claimer_id:
        raise MarketplaceTransformError(f"session {session_id} is missing poster or claimer")

    try:
        starts_at = _starts_at(document)
    except MarketplaceTransformError:
        raise MarketplaceTransformError(f"session {session_id} has no scheduled_at") from None

    post_id = str(document.get("post_id") or "").strip() or None
    post_legacy_ref = f"{exam_code}:marketplace:post:{post_id}" if post_id else None

    status, ended_at = _map_session_status(document.get("status"))
    room = str(document.get("human_practice_session_id") or "").strip() or None
    created = parse_timestamp(document.get("created_at"))
    updated = parse_timestamp(document.get("updated_at")) or created

    legacy_ref = f"{exam_code}:marketplace:session:{session_id}"
    return MigratedPeerSession(
        legacy_ref=legacy_ref,
        exam_code=exam_code,
        post_legacy_ref=post_legacy_ref,
        owner_legacy_user_id=owner_id,
        claimer_legacy_user_id=claimer_id,
        starts_at=starts_at,
        status=status,
        room_name=room,
        ended_at=ended_at or parse_timestamp(document.get("ended_at")),
        created_at=created,
        updated_at=updated,
    )


def marketplace_from_document(document: dict[str, Any]) -> MigratedAvailabilityPost | MigratedPeerSession:
    """Dispatch to the right transform by the document's `_social_kind` tag."""
    kind = str(document.get("_social_kind") or "").strip().lower()
    if kind == "post":
        return post_from_document(document)
    if kind == "session":
        return session_from_document(document)
    raise MarketplaceTransformError(f"unknown _social_kind {kind!r}")
