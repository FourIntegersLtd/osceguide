"""What an administrator changes about somebody already on the roster:

correcting the name or intake, and re-sending an invitation that never reached them.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.features.identity import service as identity
from app.features.identity import service_invitations as invitations
from app.features.roster import errors, repository, repository_groups
from app.features.roster.schemas import InvitationRead, TraineeRead, UpdateTrainee
from app.features.roster.service import _display_name, _require_trainee, _trainee_read
from app.features.tenancy import service as tenancy
from app.features.tenancy import service_audit

# The editable fields. Both a name and an intake can be blanked, so an absent
# key and an explicit null cannot be confused for one another: the first says
# "leave it", the second says "there is none".
_FIELDS = ("first_name", "last_name", "cohort_id")


async def update_trainee(
    session: AsyncSession,
    org_id: uuid.UUID,
    trainee_id: uuid.UUID,
    *,
    body: UpdateTrainee,
    fields_sent: set[str],
) -> TraineeRead:
    """Correct a roster entry: only the fields the caller actually sent.

    The address is not one of them — it identifies the entry and is what the
    account link was made against, so changing it would re-point a person's results.
    """
    await _require_trainee(session, org_id, trainee_id)
    named = set(_FIELDS) & fields_sent
    cohort_id = body.cohort_id if "cohort_id" in named else None
    # Checked against this org, so an intake from elsewhere cannot be attached
    # to a trainee here by guessing its id.
    if cohort_id is not None and await repository_groups.cohort_by_id(session, org_id, cohort_id) is None:
        raise errors.CohortNotFound()
    await repository.update_trainee(
        session,
        org_id,
        trainee_id,
        first_name=body.first_name if "first_name" in named else None,
        last_name=body.last_name if "last_name" in named else None,
        cohort_id=cohort_id,
        clear_first_name="first_name" in named and body.first_name is None,
        clear_last_name="last_name" in named and body.last_name is None,
        clear_cohort="cohort_id" in named and cohort_id is None,
    )
    refreshed = await repository.trainee_by_id(session, org_id, trainee_id)
    return _trainee_read(refreshed)  # type: ignore[arg-type]


async def delete_trainee(
    session: AsyncSession, org_id: uuid.UUID, trainee_id: uuid.UUID, *, now: datetime
) -> None:
    """Remove a roster row nobody ever examined.

    Revoking access, not deletion, is used everywhere else since a candidate's
    decision history must outlive their roster standing. This is for a row that
    never reached a decision, e.g. added by mistake. The database's `RESTRICT` on
    `candidate_result_revisions.trainee_id` is the check; see `errors.TraineeInUse`.

    Group and cohort membership cascade away with the row (`ondelete=CASCADE`).
    """
    trainee = await _require_trainee(session, org_id, trainee_id)
    try:
        await repository.delete_trainee(session, org_id, trainee_id)
    except IntegrityError as exc:
        raise errors.TraineeInUse() from exc
    await tenancy.revoke_trainee_membership(session, org_id, trainee.user_id, at=now)


async def anonymise_trainee(
    session: AsyncSession, org_id: uuid.UUID, trainee_id: uuid.UUID, *, actor: Principal, now: datetime
) -> TraineeRead:
    """GDPR erasure for a row `delete_trainee` refuses: scrub the person, keep the
    record of what was decided about them.

    Offered regardless of whether a decision exists, since it only scrubs the
    address and name, not the decision. Idempotent: re-anonymising an already
    scrubbed row is a no-op that still answers 200, not a second audit row.
    """
    trainee = await _require_trainee(session, org_id, trainee_id)
    if trainee.anonymised_at is None:
        await repository.anonymise_trainee(
            session, org_id, trainee_id, email=f"anon-{trainee_id}@anonymised.invalid", at=now
        )
        await tenancy.revoke_trainee_membership(session, org_id, trainee.user_id, at=now)
        await service_audit.record_for_org(
            session,
            org_id=org_id,
            actor=actor,
            action="trainee.anonymised",
            target_type="trainee",
            target_id=str(trainee_id),
            summary="GDPR erasure: address and name scrubbed, decisions kept",
        )
    refreshed = await repository.trainee_by_id(session, org_id, trainee_id)
    return _trainee_read(refreshed)  # type: ignore[arg-type]


async def resend_invitation(
    session: AsyncSession, org_id: uuid.UUID, trainee_id: uuid.UUID, *, now: datetime
) -> InvitationRead:
    """Send the choose-a-password link to this person again.

    The original token is stored hashed and so cannot be re-sent, only replaced;
    `identity` mints a fresh one on the same path. A row with no linked account is
    invited rather than refused, since for that person this is the first
    invitation as much as the second.
    """
    trainee = await _require_trainee(session, org_id, trainee_id)
    org = await tenancy.org_ref_by_id(session, org_id)
    invited_to = org.name if org else "your institution"
    user_id = trainee.user_id
    if user_id is None:
        # Nothing linked this trainee. If an account holds the address, link it; if
        # not, this is the first invitation rather than a repeat, and the trainee
        # gets linked on the way out.
        ref = await identity.user_ref_by_email(session, trainee.email)
        if ref is None:
            created = await invitations.invite_user(
                session,
                email=trainee.email,
                name=_display_name(trainee.first_name, trainee.last_name, trainee.email),
                invited_to=invited_to,
                now=now,
            )
            await repository.link_trainee_to_user(session, org_id, trainee_id, user_id=created.id)
            return InvitationRead(email=created.email, invited_to=invited_to)
        user_id = ref.id
        await repository.link_trainee_to_user(session, org_id, trainee_id, user_id=user_id)
    if not await invitations.reissue_invitation(session, user_id=user_id, invited_to=invited_to, now=now):
        raise errors.InvitationNotPending()
    return InvitationRead(email=trainee.email, invited_to=invited_to)
