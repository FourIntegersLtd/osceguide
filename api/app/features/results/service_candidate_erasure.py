"""An institution's request to delete one candidate's data.

Removes what identifies the candidate and what they said: their name and address on the roster,
their transcripts, and the free text written about them in decisions and appeals. Keeps what the
institution must be able to show: the attempts, the marks, and every result revision with its
outcome, signer and date. The account itself is not touched: the person may belong to other
organisations, and removing an account is the person's own `/me` erasure.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.features.attempts import service_retention
from app.features.notifications import service as notifications
from app.features.results import errors, repository, service_appeals
from app.features.results.schemas import CandidateDataDeleted
from app.features.roster import service as roster
from app.features.roster import service_edit
from app.features.tenancy import service as tenancy
from app.features.tenancy import service_audit as audit


async def erase_candidate_data(
    session: AsyncSession,
    org_id: uuid.UUID,
    trainee_id: uuid.UUID,
    *,
    confirmation: str,
    actor: Principal,
    now: datetime,
) -> CandidateDataDeleted:
    """Irreversible. The caller types the candidate's address as it stands on the roster.

    Refused while an appeal is open: a second marker needs the person's record. Repeating it on a
    candidate already erased changes nothing and writes no second audit row.
    """
    trainee = await roster.read_trainee(session, org_id, trainee_id)
    if trainee.anonymised:
        return CandidateDataDeleted(
            trainee_id=trainee_id, attempts_cleared=0, result_notes_scrubbed=0, appeals_scrubbed=0
        )
    if confirmation.strip().lower() != trainee.email.lower():
        raise errors.ConfirmationMismatch()
    if await service_appeals.has_live_appeal(session, trainee_id):
        raise errors.AppealOpenForCandidate()

    attempts = 0
    if trainee.user_id is not None:
        attempts = await service_retention.erase_for_user_in_org(session, org_id, trainee.user_id, now=now)
    notes = await repository.scrub_text_for_trainees(session, [trainee_id])
    appeals = await service_appeals.scrub_text_for_trainee(session, trainee_id)
    org = await tenancy.org_ref_by_id(session, org_id)
    if org is not None:
        await notifications.erase_result_mail(session, trainee.email, org_slug=org.slug)
    # Last, because it rewrites the address the confirmation was checked against.
    await service_edit.anonymise_trainee(session, org_id, trainee_id, actor=actor, now=now)
    await audit.record_for_owner(
        session,
        org_id=org_id,
        actor=actor,
        action="candidate_data.erased",
        target_type="trainee",
        target_id=str(trainee_id),
        summary="Candidate data deleted at the institution's request: transcripts, name, address and notes",
        meta={"attempts_cleared": attempts, "result_notes_scrubbed": notes, "appeals_scrubbed": appeals},
    )
    return CandidateDataDeleted(
        trainee_id=trainee_id,
        attempts_cleared=attempts,
        result_notes_scrubbed=notes,
        appeals_scrubbed=appeals,
    )
