"""Bulk actions on a selection of roster rows: revoke access, move to a
different intake, or resend the sign-in invitation, for many trainees in one
request.

Each row goes through the exact single-row function the individual route
uses (`service.set_access`, `service_edit.update_trainee`,
`service_edit.resend_invitation`), so a bulk action can never drift from what
the equivalent one-at-a-time click does, and writes the same audit trail.
This module only orders the calls, dedupes the input and turns each
function's outcome (or refusal) into one line of a results list, so a
partial batch — some rows changed, some already there, some not this
organisation's — is never a mystery to the caller.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.features.roster import errors, repository, repository_groups, service, service_edit
from app.features.roster.schemas import (
    BulkTraineeAccessResult,
    BulkTraineeCohortResult,
    BulkTraineeInvitationResult,
    UpdateTrainee,
)


def _dedupe_ids(trainee_ids: Sequence[uuid.UUID]) -> list[uuid.UUID]:
    """Keep the first occurrence of each id, in the order the caller sent them.

    A screen posting a selection can repeat an id (a double click, a stale
    checkbox); the result carries one row per id, not one per repetition.
    """
    return list(dict.fromkeys(trainee_ids))


async def bulk_revoke_trainees(
    session: AsyncSession,
    org_id: uuid.UUID,
    trainee_ids: Sequence[uuid.UUID],
    *,
    actor: Principal,
    now: datetime,
) -> list[BulkTraineeAccessResult]:
    """Revoke access for every trainee named, one `service.set_access` call per row.

    The row's state is read first only to tell the caller "revoked" from
    "already_revoked" apart — `set_access` itself has no third state and
    would happily re-stamp an already-revoked row with a fresh timestamp, so
    an already-revoked id is left untouched rather than re-written.
    """
    results: list[BulkTraineeAccessResult] = []
    unique_ids = _dedupe_ids(trainee_ids)
    known = await repository.trainees_by_ids(session, org_id, unique_ids)
    for trainee_id in unique_ids:
        trainee = known.get(trainee_id)
        if trainee is None:
            results.append(BulkTraineeAccessResult(trainee_id=trainee_id, outcome="not_found"))
            continue
        if trainee.access_revoked_at is not None:
            results.append(BulkTraineeAccessResult(trainee_id=trainee_id, outcome="already_revoked"))
            continue
        await service.set_access(session, org_id, trainee_id, revoked=True, actor=actor, now=now)
        results.append(BulkTraineeAccessResult(trainee_id=trainee_id, outcome="revoked"))
    return results


async def bulk_set_trainee_cohort(
    session: AsyncSession,
    org_id: uuid.UUID,
    trainee_ids: Sequence[uuid.UUID],
    *,
    cohort_id: uuid.UUID | None,
) -> list[BulkTraineeCohortResult]:
    """Move every trainee named into one intake (or clear it), one
    `service_edit.update_trainee` call per row.

    The intake is checked once, up front, against this organisation: a
    cohort from elsewhere is refused for the whole batch rather than reported
    per row, since it is a caller mistake about the request, not about any
    one trainee.
    """
    if cohort_id is not None and await repository_groups.cohort_by_id(session, org_id, cohort_id) is None:
        raise errors.CohortNotFound()
    body = UpdateTrainee(cohort_id=cohort_id)
    results: list[BulkTraineeCohortResult] = []
    for trainee_id in _dedupe_ids(trainee_ids):
        try:
            await service_edit.update_trainee(
                session, org_id, trainee_id, body=body, fields_sent={"cohort_id"}
            )
        except errors.TraineeNotFound:
            results.append(BulkTraineeCohortResult(trainee_id=trainee_id, outcome="not_found"))
            continue
        results.append(BulkTraineeCohortResult(trainee_id=trainee_id, outcome="updated"))
    return results


async def bulk_resend_trainee_invitations(
    session: AsyncSession, org_id: uuid.UUID, trainee_ids: Sequence[uuid.UUID], *, now: datetime
) -> list[BulkTraineeInvitationResult]:
    """Resend the sign-in invitation to every trainee named, one
    `service_edit.resend_invitation` call per row.

    The single-row route only ever refuses with `invitation_not_pending`
    (the person already chose a password, or the account is otherwise not
    waiting on one) — there is no rule today that refuses a revoked
    trainee, so this batch does not invent a `"revoked"` outcome for one.
    """
    results: list[BulkTraineeInvitationResult] = []
    for trainee_id in _dedupe_ids(trainee_ids):
        try:
            await service_edit.resend_invitation(session, org_id, trainee_id, now=now)
        except errors.TraineeNotFound:
            results.append(BulkTraineeInvitationResult(trainee_id=trainee_id, outcome="not_found"))
            continue
        except errors.InvitationNotPending:
            results.append(BulkTraineeInvitationResult(trainee_id=trainee_id, outcome="already_signed_in"))
            continue
        results.append(BulkTraineeInvitationResult(trainee_id=trainee_id, outcome="sent"))
    return results
