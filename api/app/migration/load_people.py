"""Loading people, their access, and the ids that connect them to attempts.

Runs before the attempts load, because a transcript names its author by
Firestore document id and nothing else can resolve that.

The general rules — re-runnable, loud, and never committing — are in
`app/migration/loader.py`.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog.models import Exam
from app.features.entitlements.models import Entitlement
from app.features.identity import repository as identity_repository
from app.features.identity.models import User
from app.migration.load_legacy_b2c import LEGACY_CONSUMER_PROVIDER
from app.migration.report import LoadReport
from app.migration.users import MergedEntitlement, MergedUser

# Marks a grant as having come from the import, and makes the grant findable on
# a second run. There is no natural key on `entitlements` because a person may
# legitimately hold several for one exam.
LEGACY_SOURCE_REF = "legacy-import"


def _apply_profile(user: User, merged: MergedUser, *, creating: bool) -> None:
    """Copy a merged user's profile fields onto a User row, in place.

    On creation everything wins; on a second run only blanks are filled and
    values that improve on what is already there (a later login, more extra
    reading time) are taken, so a person's own edits since import are kept.
    """
    if creating or not user.name.strip():
        user.name = merged.name or user.name
    if merged.last_login_at and (user.last_login_at is None or merged.last_login_at > user.last_login_at):
        user.last_login_at = merged.last_login_at
    if merged.exam_code and (creating or user.exam_code is None):
        user.exam_code = merged.exam_code
    if merged.exam_date and (creating or user.exam_date is None):
        user.exam_date = merged.exam_date
    if merged.extra_reading_percent > user.extra_reading_percent:
        user.extra_reading_percent = merged.extra_reading_percent
    # A3's replacement fields: the gate is OR'd in (once true from any legacy
    # record, it stays true) and each timer duration is only ever filled in
    # when this account does not already have one, so a person's own edit
    # since import is never overwritten by a second run.
    if merged.needs_extra_time:
        user.needs_extra_time = True
    if merged.custom_reading_seconds is not None and user.custom_reading_seconds is None:
        user.custom_reading_seconds = merged.custom_reading_seconds
    if merged.custom_simulation_seconds is not None and user.custom_simulation_seconds is None:
        user.custom_simulation_seconds = merged.custom_simulation_seconds
    if merged.consumer_role == "admin":
        user.consumer_role = "admin"
    if creating and merged.created_at:
        user.created_at = merged.created_at
    # Only ever filled, never overwritten: once this account is marked as
    # having been sent the engagement email — by legacy, or by a run of
    # `identity.jobs.send_engagement_emails` since the last import — a later
    # import must not un-send it by leaving the column blank again.
    if merged.engagement_email_sent_at and user.engagement_email_sent_at is None:
        user.engagement_email_sent_at = merged.engagement_email_sent_at


async def _link_consumer_ids(session: AsyncSession, user_id: uuid.UUID, merged: MergedUser) -> None:
    """Link every legacy Firestore document id that turned out to be this user, so re-runs recognize them."""
    linked: set[str] = set()
    for product, subject in merged.legacy_ids_by_product.items():
        if not subject or subject in linked:
            continue
        linked.add(subject)
        existing = await identity_repository.identity_by_subject(session, LEGACY_CONSUMER_PROVIDER, subject)
        if existing is None:
            await identity_repository.link_identity(
                session,
                user_id=user_id,
                provider=LEGACY_CONSUMER_PROVIDER,
                subject=subject,
                tenant_slug=product,
            )
    for subject in merged.legacy_ids:
        if subject in linked:
            continue
        existing = await identity_repository.identity_by_subject(session, LEGACY_CONSUMER_PROVIDER, subject)
        if existing is None:
            await identity_repository.link_identity(
                session,
                user_id=user_id,
                provider=LEGACY_CONSUMER_PROVIDER,
                subject=subject,
                tenant_slug=None,
            )


async def exams_by_code(session: AsyncSession) -> dict[str, uuid.UUID]:
    """Every seeded exam's id, keyed by its lowercased code."""
    exam_rows = await session.execute(select(Exam.code, Exam.id))
    return {str(code).lower(): exam_id for code, exam_id in exam_rows.all()}


async def load_users(
    session: AsyncSession,
    users: Sequence[MergedUser],
    entitlements: Sequence[MergedEntitlement] = (),
) -> tuple[LoadReport, dict[str, uuid.UUID], dict[str, uuid.UUID]]:
    """Load people and their access. Returns the report and legacy id -> user id.

    The mapping is the reason this runs first: a transcript names its author by
    Firestore document id, and nothing else can resolve that.
    """
    report = LoadReport()
    by_legacy_id: dict[str, uuid.UUID] = {}
    by_email: dict[str, uuid.UUID] = {}

    for merged in users:
        email = merged.email.strip().lower()
        if not email:
            report.problem(f"A merged user has no email and was not loaded: {merged!r}")
            continue

        existing = await session.scalar(select(User).where(User.email == email))
        if existing is None:
            user = User(
                email=email,
                name=merged.name,
                # A b2c bcrypt hash goes to the legacy column, never to `password_hash`; sign-in
                # accepts it once and replaces it with argon2id. Insert only: a second run must not
                # give a legacy hash back to someone who has since signed in or reset.
                password_hash=None,
                legacy_password_hash=merged.legacy_password_hash,
                must_change_password=merged.must_reset_password,
                is_platform_admin=merged.is_platform_admin,
                exam_code=merged.exam_code,
                exam_date=merged.exam_date,
                extra_reading_percent=merged.extra_reading_percent,
                needs_extra_time=merged.needs_extra_time,
                custom_reading_seconds=merged.custom_reading_seconds,
                custom_simulation_seconds=merged.custom_simulation_seconds,
                consumer_role=merged.consumer_role,
                last_login_at=merged.last_login_at,
            )
            session.add(user)
            await session.flush()
            _apply_profile(user, merged, creating=True)
            report.users_created += 1
        else:
            # A second run, or somebody who signed up before their import.
            # Their password (and any legacy hash) and status are theirs now; only the platform
            # admin flag is re-asserted, because that is an access decision
            # the export is authoritative about.
            user = existing
            if merged.is_platform_admin and not user.is_platform_admin:
                user.is_platform_admin = True
            _apply_profile(user, merged, creating=False)
            report.users_matched += 1

        await _link_consumer_ids(session, user.id, merged)
        by_email[email] = user.id
        for legacy_id in merged.legacy_ids:
            if legacy_id in by_legacy_id and by_legacy_id[legacy_id] != user.id:
                report.problem(
                    f"Legacy id {legacy_id!r} maps to two different people; "
                    "attempts referencing it were not loaded."
                )
                continue
            by_legacy_id[legacy_id] = user.id

    exams = await exams_by_code(session)
    for grant in entitlements:
        email = grant.email.strip().lower()
        user_id = by_email.get(email)
        if user_id is None:
            report.problem(f"Entitlement for {email!r}, who is not in the user export.")
            continue
        exam_id = exams.get(grant.exam_code.lower())
        if exam_id is None:
            report.problem(f"Entitlement names exam {grant.exam_code!r}, which is not seeded.")
            continue

        already = await session.scalar(
            select(Entitlement.id).where(
                Entitlement.user_id == user_id,
                Entitlement.exam_id == exam_id,
                Entitlement.source_ref == LEGACY_SOURCE_REF,
            )
        )
        if already is not None:
            report.entitlements_existing += 1
            continue

        session.add(
            Entitlement(
                user_id=user_id,
                exam_id=exam_id,
                source=grant.source,
                source_ref=LEGACY_SOURCE_REF,
                starts_at=grant.starts_at or datetime.now(UTC),
                # Expired grants come across too: "your access ended in March"
                # is a better answer than an empty list.
                ends_at=grant.ends_at,
            )
        )
        report.entitlements_created += 1

    await session.flush()
    return report, by_legacy_id, by_email


async def backfill_legacy_passwords(session: AsyncSession, users: Sequence[MergedUser]) -> LoadReport:
    """Give accounts imported before legacy hashes were carried their b2c hash.

    Only where `identity_repository.backfill_legacy_password` finds no credential at all and the
    import's identity link, so it is safe to re-run and touches nobody who can already sign in."""
    report = LoadReport()
    for merged in users:
        if merged.legacy_password_hash is None:
            continue
        if await identity_repository.backfill_legacy_password(
            session,
            email=merged.email,
            legacy_password_hash=merged.legacy_password_hash,
            identity_provider=LEGACY_CONSUMER_PROVIDER,
        ):
            report.legacy_passwords_backfilled += 1
    return report
