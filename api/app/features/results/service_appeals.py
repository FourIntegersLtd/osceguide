"""Appeals against a released result: asked for, given a second marker, then upheld, changed or declined.

A released result is final, so the outcome of an appeal is never an edit: it is a new
released revision that supersedes the one under review, written in the same transaction
as the appeal's decision. Nothing here touches an old revision.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.core.errors import raise_mapped
from app.features.identity import service as identity
from app.features.notifications import service as notifications
from app.features.results import domain, errors, repository, repository_appeals, service, service_candidate
from app.features.results.models import CandidateResultRevision, ResultAppeal
from app.features.results.schemas import (
    AppealPage,
    AppealRead,
    AssignAppeal,
    CandidateAppealRead,
    DeclineAppeal,
    ResolveAppeal,
)
from app.features.roster import service as roster
from app.features.sittings import service_reads as sittings
from app.features.tenancy import service as tenancy
from app.features.tenancy import service_audit as audit

LIVE = repository_appeals.LIVE


async def request_as_candidate(
    session: AsyncSession, *, sitting_id: uuid.UUID, principal: Principal, reason: str
) -> CandidateAppealRead:
    """The signed-in candidate asks for their own released result to be looked at again."""
    released = await service_candidate.require_released_revision(session, sitting_id, principal.user_id)
    appeal = await _open(session, released, reason=reason, actor=principal, on_behalf=False)
    return _candidate_read(appeal)


async def request_for_candidate(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    sitting_id: uuid.UUID,
    trainee_id: uuid.UUID,
    reason: str,
    actor: Principal,
) -> AppealRead:
    """Staff record a request the candidate made to them, on the candidate's behalf."""
    latest = await repository.latest_revision(session, org_id, sitting_id, trainee_id)
    if latest is None or latest.workflow_state != "released":
        raise errors.NotReleased()
    appeal = await _open(session, latest, reason=reason, actor=actor, on_behalf=True)
    return (await _read_many(session, org_id, [appeal]))[0]


async def my_appeal(
    session: AsyncSession, *, sitting_id: uuid.UUID, user_id: uuid.UUID
) -> CandidateAppealRead | None:
    """The newest review this candidate asked for on the sitting, or null."""
    trainee_ids = await roster.trainee_ids_for_user(session, user_id)
    appeal = await repository_appeals.latest_for_candidate(session, sitting_id, trainee_ids)
    return None if appeal is None else _candidate_read(appeal)


async def queue(session: AsyncSession, org_id: uuid.UUID, *, live: bool | None) -> AppealPage:
    """The organisation's appeals: waiting first (`live`), or the decided ones."""
    appeals = await repository_appeals.listed(session, org_id, live=live)
    return AppealPage(appeals=await _read_many(session, org_id, appeals))


async def assign(
    session: AsyncSession,
    org_id: uuid.UUID,
    appeal_id: uuid.UUID,
    body: AssignAppeal,
    *,
    actor: Principal,
    now: datetime,
) -> AppealRead:
    """Name the second marker. Not the person who signed off or released the result under review."""
    appeal = await _live(session, org_id, appeal_id)
    original = await _original_revision(session, appeal)
    if body.assignee_user_id in _original_marker_ids(original):
        raise errors.SecondMarkerMustDiffer()
    if body.assignee_user_id not in await tenancy.admin_user_ids(session, org_id):
        raise errors.AssigneeNotAdmin()
    await repository_appeals.assign(session, appeal, assignee=body.assignee_user_id, at=now)
    await _audit(session, appeal, actor, "result_appeal.assigned", {"assignee": str(body.assignee_user_id)})
    return (await _read_many(session, org_id, [appeal]))[0]


async def decline(
    session: AsyncSession,
    org_id: uuid.UUID,
    appeal_id: uuid.UUID,
    body: DeclineAppeal,
    *,
    actor: Principal,
    now: datetime,
) -> AppealRead:
    """Turn the request down with a reason the candidate is sent. The result stays as it was."""
    appeal = await _live(session, org_id, appeal_id)
    await repository_appeals.settle(
        session,
        appeal,
        status="declined",
        decided_by=actor.user_id,
        at=now,
        note=body.reason,
        outcome_revision=None,
    )
    await _tell_candidate(
        session, appeal, template_key="candidate_appeal_declined", subject="Your review request"
    )
    await _audit(session, appeal, actor, "result_appeal.declined", {})
    return (await _read_many(session, org_id, [appeal]))[0]


async def resolve(
    session: AsyncSession,
    org_id: uuid.UUID,
    appeal_id: uuid.UUID,
    body: ResolveAppeal,
    *,
    actor: Principal,
    now: datetime,
) -> AppealRead:
    """The second marker's decision, appended as a new released revision of the result.

    Always a new revision, even when the outcome is unchanged, so the result history shows
    the review happened. The earlier revisions are untouched.
    """
    appeal = await _live(session, org_id, appeal_id)
    if appeal.status != "in_review" or appeal.assigned_to is None:
        raise errors.AppealNotAssigned()
    if appeal.assigned_to != actor.user_id:
        raise errors.NotAssignedMarker()
    latest = await repository.latest_revision(session, org_id, appeal.sitting_id, appeal.trainee_id)
    if latest is None or latest.revision != appeal.revision:
        raise errors.AppealStale()
    recruitment = body.recruitment_outcome or latest.recruitment_outcome
    try:
        domain.ensure_compatible(
            domain.Assessment(body.assessment_outcome),
            None if recruitment is None else domain.Recruitment(recruitment),
        )
    except domain.IncompatibleOutcomes as exc:
        raise_mapped(exc, service.REFUSALS)
    await service.ensure_hire_reason(session, org_id, recruitment, body.rationale)

    revised = await repository.append_revision(
        session,
        org_id,
        sitting_id=appeal.sitting_id,
        trainee_id=appeal.trainee_id,
        revision=domain.next_revision(latest.revision),
        supersedes_revision=latest.revision,
        workflow_state=str(domain.Workflow.RELEASED),
        assessment_outcome=body.assessment_outcome,
        recruitment_outcome=recruitment,
        rationale=body.rationale,
        moderation_notes=latest.moderation_notes,
        evidence_snapshot=latest.evidence_snapshot,
        evidence_fingerprint=latest.evidence_fingerprint,
        created_by=actor.user_id,
        signed_off_by=actor.user_id,
        signed_off_at=now,
        released_by=actor.user_id,
        released_at=now,
    )
    await repository.append_event(
        session,
        revision_id=revised.id,
        event_type="appeal_resolved",
        actor_user_id=actor.user_id,
        idempotency_key=f"appeal_resolved:{appeal.id}",
    )
    await repository_appeals.settle(
        session,
        appeal,
        status="resolved",
        decided_by=actor.user_id,
        at=now,
        note=None,
        outcome_revision=revised.revision,
    )
    await _tell_candidate(
        session, appeal, template_key="candidate_result_revised", subject="Your result has been reviewed"
    )
    await _audit(
        session,
        appeal,
        actor,
        "result_appeal.resolved",
        {"from": latest.assessment_outcome, "to": body.assessment_outcome, "revision": revised.revision},
    )
    return (await _read_many(session, org_id, [appeal]))[0]


async def has_live_appeal(session: AsyncSession, trainee_id: uuid.UUID) -> bool:
    """Whether this candidate's data is still needed for an appeal, so it must not be deleted."""
    return await repository_appeals.live_for_trainee(session, trainee_id)


async def scrub_text_for_trainee(session: AsyncSession, trainee_id: uuid.UUID) -> int:
    """A candidate's data is being deleted: their appeal text becomes `[erased]`; the rows stay."""
    return await repository_appeals.scrub_text_for_trainee(session, trainee_id)


async def _open(
    session: AsyncSession,
    released: CandidateResultRevision,
    *,
    reason: str,
    actor: Principal,
    on_behalf: bool,
) -> ResultAppeal:
    """Write the appeal and its audit row against the candidate's released revision."""
    appeal = await repository_appeals.add(
        session,
        org_id=released.org_id,
        sitting_id=released.sitting_id,
        trainee_id=released.trainee_id,
        revision=released.revision,
        reason=reason.strip(),
        requested_by=actor.user_id,
        on_behalf=on_behalf,
    )
    await _audit(session, appeal, actor, "result_appeal.requested", {"on_behalf": on_behalf})
    return appeal


async def _live(session: AsyncSession, org_id: uuid.UUID, appeal_id: uuid.UUID) -> ResultAppeal:
    """The appeal with its row locked, and still waiting for a decision."""
    appeal = await repository_appeals.locked(session, org_id, appeal_id)
    if appeal is None:
        raise errors.AppealNotFound()
    if appeal.status not in LIVE:
        raise errors.AppealClosed()
    return appeal


async def _original_revision(session: AsyncSession, appeal: ResultAppeal) -> CandidateResultRevision | None:
    """The revision the appeal was asked against, as it was released."""
    return await repository_appeals.revision_row(
        session, appeal.org_id, appeal.sitting_id, appeal.trainee_id, appeal.revision
    )


def _original_marker_ids(revision: CandidateResultRevision | None) -> set[uuid.UUID]:
    """Who signed off and released that revision: none of them may re-mark it."""
    if revision is None:
        return set()
    return {user for user in (revision.signed_off_by, revision.released_by) if user is not None}


async def _tell_candidate(
    session: AsyncSession, appeal: ResultAppeal, *, template_key: str, subject: str
) -> None:
    """Queue the email on the shared outbox, in this transaction, like a release."""
    org = await tenancy.org_ref_by_id(session, appeal.org_id)
    if org is None:
        raise errors.ResultNotFound()
    recipient = await roster.trainee_email(session, appeal.org_id, appeal.trainee_id)
    await notifications.enqueue_email(
        session,
        recipient=recipient,
        subject=subject,
        template_key=template_key,
        payload={"sitting_id": str(appeal.sitting_id), "org_slug": org.slug, "org_name": org.name},
        idempotency_key=f"{template_key}:{appeal.id}",
    )


async def _audit(
    session: AsyncSession, appeal: ResultAppeal, actor: Principal, action: str, meta: dict[str, object]
) -> None:
    """One audit row for an appeal, naming the sitting and candidate by id and holding no personal data."""
    await audit.record_for_owner(
        session,
        org_id=appeal.org_id,
        actor=actor,
        action=action,
        target_type="result_appeal",
        target_id=str(appeal.id),
        summary=None,
        meta={"sitting_id": str(appeal.sitting_id), "trainee_id": str(appeal.trainee_id), **meta},
    )


def _candidate_read(appeal: ResultAppeal) -> CandidateAppealRead:
    """What the candidate sees of their request: the reason, the status and any decline note."""
    return CandidateAppealRead(
        id=appeal.id,
        sitting_id=appeal.sitting_id,
        status=appeal.status,
        reason=appeal.reason,
        requested_at=appeal.created_at,
        decided_at=appeal.decided_at,
        decision_note=appeal.decision_note if appeal.status == "declined" else None,
    )


async def _read_many(
    session: AsyncSession, org_id: uuid.UUID, appeals: list[ResultAppeal]
) -> list[AppealRead]:
    """Appeals with the names the queue shows, in a few lookups rather than one per row."""
    people = await identity.user_refs_by_ids(
        session, [appeal.assigned_to for appeal in appeals if appeal.assigned_to is not None]
    )
    reads: list[AppealRead] = []
    for appeal in appeals:
        sitting = await sittings.sitting_ref(session, org_id, appeal.sitting_id)
        trainee = await roster.read_trainee(session, org_id, appeal.trainee_id)
        shown = " ".join(part for part in (trainee.first_name, trainee.last_name) if part) or trainee.email
        original = await _original_revision(session, appeal)
        reads.append(
            AppealRead(
                id=appeal.id,
                sitting_id=appeal.sitting_id,
                sitting_name=None if sitting is None else sitting.name,
                trainee_id=appeal.trainee_id,
                candidate_name="Deleted candidate" if trainee.anonymised else shown,
                status=appeal.status,
                reason=appeal.reason,
                on_behalf=appeal.on_behalf,
                requested_at=appeal.created_at,
                revision=appeal.revision,
                original_outcome=None if original is None else original.assessment_outcome,
                outcome_revision=appeal.outcome_revision,
                original_marker_ids=sorted(_original_marker_ids(original)),
                assigned_to=appeal.assigned_to,
                assigned_to_name=(
                    people[appeal.assigned_to].name
                    if appeal.assigned_to is not None and appeal.assigned_to in people
                    else None
                ),
                assigned_at=appeal.assigned_at,
                decision_note=appeal.decision_note,
                decided_at=appeal.decided_at,
            )
        )
    return reads
