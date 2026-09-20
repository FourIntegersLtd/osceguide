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


def _apply_profile(row: User, merged: MergedUser, *, creating: bool) -> None:
    if creating or not row.name.strip():
        row.name = merged.name or row.name
    if merged.last_login_at and (row.last_login_at is None or merged.last_login_at > row.last_login_at):
        row.last_login_at = merged.last_login_at
    if merged.exam_code and (creating or row.exam_code is None):
        row.exam_code = merged.exam_code
    if merged.exam_date and (creating or row.exam_date is None):
        row.exam_date = merged.exam_date
    if merged.extra_reading_percent > row.extra_reading_percent:
        row.extra_reading_percent = merged.extra_reading_percent
    if merged.consumer_role == "admin":
        row.consumer_role = "admin"
    if creating and merged.created_at:
        row.created_at = merged.created_at


async def _link_consumer_ids(session: AsyncSession, user_id: uuid.UUID, merged: MergedUser) -> None:
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
    rows = await session.execute(select(Exam.code, Exam.id))
    return {str(code).lower(): exam_id for code, exam_id in rows.all()}


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
            row = User(
                email=email,
                name=merged.name,
                # Neither legacy hash is argon2 and b2b's is unsalted SHA-256,
                # so nobody's password comes across and everybody resets.
                password_hash=None,
                must_change_password=merged.must_reset_password,
                is_platform_admin=merged.is_platform_admin,
                exam_code=merged.exam_code,
                exam_date=merged.exam_date,
                extra_reading_percent=merged.extra_reading_percent,
                consumer_role=merged.consumer_role,
                last_login_at=merged.last_login_at,
            )
            session.add(row)
            await session.flush()
            _apply_profile(row, merged, creating=True)
            report.users_created += 1
        else:
            # A second run, or somebody who signed up before their import.
            # Their password and status are theirs now; only the platform
            # admin flag is re-asserted, because that is an access decision
            # the export is authoritative about.
            row = existing
            if merged.is_platform_admin and not row.is_platform_admin:
                row.is_platform_admin = True
            _apply_profile(row, merged, creating=False)
            report.users_matched += 1

        await _link_consumer_ids(session, row.id, merged)
        by_email[email] = row.id
        for legacy_id in merged.legacy_ids:
            if legacy_id in by_legacy_id and by_legacy_id[legacy_id] != row.id:
                report.problem(
                    f"Legacy id {legacy_id!r} maps to two different people; "
                    "attempts referencing it were not loaded."
                )
                continue
            by_legacy_id[legacy_id] = row.id

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
