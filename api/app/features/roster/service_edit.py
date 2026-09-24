"""What an administrator changes about somebody already on the roster.

Split from `service.py` by the row's own story: that module brings a person
onto the roster, this one deals with the entry afterwards — correcting the
name or the intake it was written with, and re-sending the invitation that
never reached them. Both are per-row actions on the same screen, and neither
is the act of rostering somebody.
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

    The address is not one of them. It is what identifies the entry inside the
    organisation and what the account link was made against, so changing it is
    re-pointing a person's results rather than fixing a typo — which is also
    what the legacy edit screen refused to offer.
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


async def delete_trainee(session: AsyncSession, org_id: uuid.UUID, trainee_id: uuid.UUID) -> None:
    """Remove a roster row nobody ever examined.

    Revoking access is what this product uses everywhere else — it is
    reversible, and a candidate's decision history is meant to outlive their
    standing on a roster. This exists for the row that never got that far: a
    trainee added by mistake, or one who left before a circuit ever ran, where
    there is no decision for `trainee_in_use` to be protecting.

    `roster` sits below `results` in the layer contract (`pyproject.toml`'s
    `import-linter` config) and cannot ask "does this trainee have a
    decision" itself, the same limit `catalog.delete_exam` hit — see
    `errors.TraineeInUse`. The database's `RESTRICT` on
    `candidate_result_revisions.trainee_id` is the check, caught here.

    Group and cohort membership cascade away with the row (`ondelete=CASCADE`
    on both) — that is bookkeeping the trainee owned, not a record about them.
    """
    await _require_trainee(session, org_id, trainee_id)
    try:
        await repository.delete_trainee(session, org_id, trainee_id)
    except IntegrityError as exc:
        raise errors.TraineeInUse() from exc


async def anonymise_trainee(
    session: AsyncSession, org_id: uuid.UUID, trainee_id: uuid.UUID, *, actor: Principal, now: datetime
) -> TraineeRead:
    """GDPR erasure for a row `delete_trainee` refuses: scrub the person, keep
    the record of what was decided about them.

    Unlike `delete_trainee`, this is offered regardless of whether a decision
    exists — it never destroys anything, only the address and name that name
    the person, so there is nothing for a `RESTRICT` to protect it from.
    Idempotent: anonymising an already-anonymised row is a no-op that still
    answers 200, the same shape the station-flags idempotency uses, so a
    retried request is not a second audit row for the same act.
    """
    row = await _require_trainee(session, org_id, trainee_id)
    if row.anonymised_at is None:
        await repository.anonymise_trainee(
            session, org_id, trainee_id, email=f"anon-{trainee_id}@anonymised.invalid", at=now
        )
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

    An institution rosters by address long before the person signs in, and the
    one email it sends can be lost — with nothing to press and say "send it
    again", so the candidate sits unexamined while the organisation believes it
    told them.

    The link in that first email cannot be repeated, only replaced: the token
    is stored hashed, which is what makes it worthless to anyone who intercepts
    the message, including us. `identity` mints a fresh one on the same path.

    A row whose account link is empty — as the migration leaves them — is
    invited rather than refused, because for that person this is the first
    invitation as much as the second.
    """
    row = await _require_trainee(session, org_id, trainee_id)
    org = await tenancy.org_ref_by_id(session, org_id)
    invited_to = org.name if org else "your institution"
    user_id = row.user_id
    if user_id is None:
        # Nothing linked this row. If an account holds the address, link it; if
        # not, this is the first invitation rather than a repeat, and the row
        # gets linked on the way out.
        ref = await identity.user_ref_by_email(session, row.email)
        if ref is None:
            created = await invitations.invite_user(
                session,
                email=row.email,
                name=_display_name(row.first_name, row.last_name, row.email),
                invited_to=invited_to,
                now=now,
            )
            await repository.link_trainee_to_user(session, org_id, trainee_id, user_id=created.id)
            return InvitationRead(email=created.email, invited_to=invited_to)
        user_id = ref.id
        await repository.link_trainee_to_user(session, org_id, trainee_id, user_id=user_id)
    if not await invitations.reissue_invitation(session, user_id=user_id, invited_to=invited_to, now=now):
        raise errors.InvitationNotPending()
    return InvitationRead(email=row.email, invited_to=invited_to)
