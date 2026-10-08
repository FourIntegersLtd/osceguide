"""Practice access: an institution or partner giving people an exam to practise, by email.

Replaces b2b's practice users (`/orgs/{slug}/practice-users`), which kept a second list of
people and a second entitlement table beside the real ones. Here a practice-access row *is*
an entitlement — source `org_grant`, `org_id` set — so the one gate every attempt passes
(`service.require`) honours it and revoking it closes that gate.

A person who has no account yet is invited through `identity.service_invitations`, the same
machinery memberships and rosters use: the account is created now, with no password, and the
entitlement is attached to it straight away. The account cannot sign in until its owner
follows the emailed link and chooses a password, which is what proves they own the address.
So the access is live on paper from the start but unusable by anyone else, and there is no
pending-grant table to reconcile at sign-up.

Only exams this organisation actually offers may be granted: its own published exams, and
platform exams it has imported (`catalog.exam_offered_by_org`).
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.features.catalog import service as catalog
from app.features.catalog.errors import UnknownExamError as CatalogUnknownExam
from app.features.catalog.service import ExamRef
from app.features.entitlements import errors, repository, service
from app.features.entitlements.models import Entitlement
from app.features.entitlements.schemas import (
    PracticeAccessRead,
    PracticeAccessResult,
    PracticeAccessRow,
    PracticeAccessStatus,
)
from app.features.identity import service as identity
from app.features.identity import service_invitations as invitations
from app.features.identity.service import UserRef
from app.features.notifications import service as notifications
from app.features.tenancy import service as tenancy

# Every practice-access row is an organisation's grant; other sources (a purchase, an SSO
# tenant) are never listed or revoked through these routes.
PRACTICE_ACCESS_SOURCE = "org_grant"

# Deliberately loose: one `@`, something either side, a dot in the domain. The emailed link
# is the real proof an address works; this only stops a CSV's stray header or blank cell.
_EMAIL_SHAPE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class _Provisioned:
    """What granting one person one exam did, before it is shaped for a route."""

    outcome: Literal["granted", "invited", "already_active"]
    entitlement: Entitlement | None


def _normalised_email(raw: str) -> str | None:
    """The address as accounts store it, or `None` if it is not shaped like an email address."""
    email = identity.normalized_email(raw)
    return email if len(email) <= 320 and _EMAIL_SHAPE.match(email) else None


async def list_practice_access(
    session: AsyncSession, org_id: uuid.UUID, *, now: datetime
) -> list[PracticeAccessRead]:
    """Everything this organisation has granted as practice access, newest first.

    Revoked, expired and suspended rows are included, each marked as such: this is the history an
    administrator reads, not a gate. The gate is `service.require`.
    """
    grants = await repository.grants_by_source_for_org(session, org_id, source=PRACTICE_ACCESS_SOURCE)
    return await _practice_reads(session, grants, now=now)


async def grant_practice_access(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    email: str,
    exam_id: uuid.UUID,
    actor: Principal,
    now: datetime,
) -> PracticeAccessRead:
    """Give one person practice access to one exam this organisation offers.

    An existing account gets a live grant and a notification email; an unknown address is
    invited (see the module docstring). Refused `invalid_email` (422), `unknown_exam` (404)
    for an exam this organisation does not offer, and `practice_access_exists` (409) when
    this organisation already gives this person this exam.
    """
    normalised_email = _normalised_email(email)
    if normalised_email is None:
        raise errors.InvalidPracticeEmail()
    try:
        exam = await catalog.exam_offered_by_org(session, org_id, exam_id)
    except CatalogUnknownExam as exc:
        raise errors.UnknownExamError(str(exc)) from exc
    provisioned = await _provision(
        session,
        org_id,
        org_name=await _org_name(session, org_id),
        email=normalised_email,
        exam=exam,
        actor=actor,
        now=now,
    )
    if provisioned.entitlement is None:
        raise errors.PracticeAccessExists()
    return (await _practice_reads(session, [provisioned.entitlement], now=now))[0]


async def grant_practice_access_in_bulk(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    rows: Sequence[PracticeAccessRow],
    actor: Principal,
    now: datetime,
) -> list[PracticeAccessResult]:
    """Grant each row in turn and report what happened to it, never refusing the batch.

    A row that cannot be granted says why (`invalid_email`, `unknown_exam`) and the rest
    carry on. A repeat of a live grant — including the same row twice in one file — is
    `already_active` and sends nothing.
    """
    org_name = await _org_name(session, org_id)
    exams_by_cell: dict[str, ExamRef | None] = {}
    results: list[PracticeAccessResult] = []
    for row in rows:
        normalised_email = _normalised_email(row.email)
        if normalised_email is None:
            results.append(PracticeAccessResult(email=row.email.strip(), outcome="invalid_email"))
            continue
        exam_cell = row.exam_id.strip()
        if exam_cell not in exams_by_cell:
            exams_by_cell[exam_cell] = await _offered_exam_or_none(session, org_id, exam_cell)
        exam = exams_by_cell[exam_cell]
        if exam is None:
            results.append(PracticeAccessResult(email=normalised_email, outcome="unknown_exam"))
            continue
        provisioned = await _provision(
            session, org_id, org_name=org_name, email=normalised_email, exam=exam, actor=actor, now=now
        )
        results.append(PracticeAccessResult(email=normalised_email, outcome=provisioned.outcome))
    return results


async def revoke_practice_access(
    session: AsyncSession, org_id: uuid.UUID, access_id: uuid.UUID, *, actor: Principal, now: datetime
) -> PracticeAccessRead:
    """Withdraw one practice-access grant. The row stays, with `revoked_at`, so history holds.

    Revoking twice is harmless and answers the same row. Another organisation's grant, or a
    grant from any other source, is `entitlement_not_found` (404) exactly as a missing one is.
    """
    grant = await repository.by_id_for_org(session, org_id, access_id)
    if grant is None or grant.source != PRACTICE_ACCESS_SOURCE:
        raise errors.EntitlementNotFound()
    if grant.revoked_at is None:
        await repository.revoke(session, grant.id, at=now)
        await session.refresh(grant)
        await tenancy.record_audit(
            session,
            org_id=org_id,
            actor_user_id=actor.user_id,
            actor_email=actor.email,
            action="practice_access.revoked",
            target_type="entitlement",
            target_id=str(grant.id),
        )
    return (await _practice_reads(session, [grant], now=now))[0]


async def _provision(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    org_name: str,
    email: str,
    exam: ExamRef,
    actor: Principal,
    now: datetime,
) -> _Provisioned:
    """Grant one normalised address one offered exam: the step single and bulk grants share.

    Three paths. A live grant from this organisation already exists: nothing is written.
    No account: one is invited, and the invitation email names the exam. An account still
    waiting on an earlier invitation: that invitation is sent again, naming the exam, since
    a "you can now practise" email is useless to someone who cannot yet sign in. Otherwise
    the grant email goes out. Every write is audited.
    """
    person: UserRef | None = await identity.user_ref_by_email(session, email)
    if person is not None and await repository.live_grant_from_org(
        session, org_id, user_id=person.id, exam_id=exam.id, source=PRACTICE_ACCESS_SOURCE, now=now
    ):
        return _Provisioned(outcome="already_active", entitlement=None)
    invited = False
    if person is None:
        person = await invitations.invite_user(
            session, email=email, name=email, invited_to=org_name, now=now, practice_exam_title=exam.name
        )
        invited = True
    elif person.invitation_pending:
        invited = await invitations.reissue_invitation(
            session, user_id=person.id, invited_to=org_name, now=now, practice_exam_title=exam.name
        )
    entitlement = await repository.grant(
        session,
        user_id=person.id,
        exam_id=exam.id,
        source=PRACTICE_ACCESS_SOURCE,
        source_ref=str(org_id),
        org_id=org_id,
        starts_at=now,
        granted_by=actor.user_id,
    )
    if not invited:
        await notifications.enqueue_email(
            session,
            recipient=person.email,
            subject=f"{org_name} has given you practice access to {exam.name}",
            template_key="practice_access_granted",
            payload={"exam_title": exam.name, "granted_by": org_name},
            idempotency_key=f"practice_access_granted:{entitlement.id}",
        )
    await tenancy.record_audit(
        session,
        org_id=org_id,
        actor_user_id=actor.user_id,
        actor_email=actor.email,
        action="practice_access.invited" if invited else "practice_access.granted",
        target_type="entitlement",
        target_id=str(entitlement.id),
        summary=f"{email} for {exam.code}" + (" (invited)" if invited else ""),
    )
    return _Provisioned(outcome="invited" if invited else "granted", entitlement=entitlement)


async def _offered_exam_or_none(session: AsyncSession, org_id: uuid.UUID, exam_cell: str) -> ExamRef | None:
    """The exam a CSV cell names, if it is a uuid this organisation offers; otherwise `None`."""
    try:
        exam_id = uuid.UUID(exam_cell)
    except ValueError:
        return None
    try:
        return await catalog.exam_offered_by_org(session, org_id, exam_id)
    except CatalogUnknownExam:
        return None


async def _org_name(session: AsyncSession, org_id: uuid.UUID) -> str:
    """The organisation's name as the emails say it."""
    organisation = await tenancy.org_ref_by_id(session, org_id)
    return organisation.name if organisation is not None else "your organisation"


async def _practice_reads(
    session: AsyncSession, grants: Sequence[Entitlement], *, now: datetime
) -> list[PracticeAccessRead]:
    """Shape grants for a route, looking the people and exams up once for the whole list."""
    people = await identity.user_refs_by_ids(session, [grant.user_id for grant in grants])
    exams = await catalog.exam_refs_by_ids(session, list({grant.exam_id for grant in grants}))
    held = await service.held_by_inactive_org(session, grants, now=now)
    reads = []
    for grant in grants:
        person = people.get(grant.user_id)
        exam = exams.get(grant.exam_id)
        status, revoked_at = _practice_status(grant, person, now=now, suspended=grant.id in held)
        reads.append(
            PracticeAccessRead(
                access_id=grant.id,
                email=person.email if person is not None else "",
                user_id=grant.user_id,
                exam_id=grant.exam_id,
                exam_code=exam.code if exam is not None else "",
                exam_title=exam.name if exam is not None else "",
                status=status,
                granted_at=grant.starts_at,
                revoked_at=revoked_at,
            )
        )
    return reads


def _practice_status(
    grant: Entitlement, person: UserRef | None, *, now: datetime, suspended: bool
) -> tuple[PracticeAccessStatus, datetime | None]:
    """Which state a grant is in, and when an administrator withdrew it if one did.

    `revoked` is an administrator's act. A grant whose end date passed is `expired`, and one
    made by an organisation that is currently suspended is `suspended` (S-15); all grant
    nothing. A live grant to an account nobody has used yet is `invited`.
    """
    if grant.revoked_at is not None:
        return "revoked", grant.revoked_at
    if not service._to_grant(grant).live_at(now):
        return "expired", None
    if suspended:
        return "suspended", None
    if person is not None and person.invitation_pending:
        return "invited", None
    return "active", None
