"""Use cases for the people an organisation teaches: adding a trainee, listing
them, revoking or restoring access, and answering which organisations and
teaching groups a signed-in person belongs to.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audience import ViewerAudiences
from app.features.catalog import service as catalog
from app.features.identity import service as identity
from app.features.identity import service_invitations as invitations
from app.features.roster import domain, errors, repository, repository_groups
from app.features.roster.models import Trainee
from app.features.roster.schemas import (
    BulkTraineesResult,
    CreateTrainee,
    SkippedTrainee,
    TraineeRead,
)
from app.features.sittings import service_reads as sittings
from app.features.tenancy import service as tenancy


async def add_trainee(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    email: str,
    first_name: str | None,
    last_name: str | None,
    cohort_id: uuid.UUID | None,
    now: datetime,
) -> TraineeRead:
    """Add a trainee to an organisation's roster and invite them, if needed.

    Every trainee ends up linked to an account: a slot names a `users.id`, so an
    unlinked trainee could be rostered and never scheduled.
    """
    if await repository.trainee_by_email(session, org_id, email) is not None:
        raise errors.TraineeExists()
    trainee = await repository.create_trainee(
        session,
        org_id,
        email=email,
        first_name=first_name,
        last_name=last_name,
        cohort_id=cohort_id,
    )
    # A slot names a `users.id`, so a trainee without a linked account could be
    # rostered and never scheduled. Invite and link now, so every trainee has one.
    existing = await identity.user_ref_by_email(session, email)
    if existing is None:
        org = await tenancy.org_ref_by_id(session, org_id)
        existing = await invitations.invite_user(
            session,
            email=email,
            name=_display_name(first_name, last_name, email),
            invited_to=org.name if org else "your institution",
            now=now,
        )
    await repository.link_trainee_to_user(session, org_id, trainee.id, user_id=existing.id)
    await session.refresh(trainee)
    return _trainee_read(trainee)


def _display_name(first: str | None, last: str | None, email: str) -> str:
    return " ".join(part for part in (first, last) if part) or email


async def list_trainees(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    limit: int,
    cursor: dict[str, Any] | None,
    search: str | None = None,
    access_revoked: bool | None = None,
) -> tuple[list[TraineeRead], str | None]:
    """A page of an organisation's roster, optionally narrowed to a trainee
    whose name, email or cohort matches `search`, and to revoked or live access."""
    trainees, next_cursor = await repository.list_trainees(
        session, org_id, limit=limit, cursor=cursor, search=search, access_revoked=access_revoked
    )
    reads = [_trainee_read(trainee) for trainee in trainees]
    sat, programme_ids = await sittings.trainee_activity(
        session, org_id, [trainee.user_id for trainee in trainees if trainee.user_id is not None]
    )
    names = await catalog.programme_names(
        session, org_id, sorted({pid for pids in programme_ids.values() for pid in pids}, key=str)
    )
    for read in reads:
        if read.user_id is None:
            continue
        read.stations_sat = sat.get(read.user_id, 0)
        read.programme_names = sorted(
            {names[pid] for pid in programme_ids.get(read.user_id, set()) if pid in names}
        )
    return reads, next_cursor


async def set_access(
    session: AsyncSession,
    org_id: uuid.UUID,
    trainee_id: uuid.UUID,
    *,
    revoked: bool,
    now: datetime,
) -> TraineeRead:
    """Revoke or restore a trainee's access to their organisation."""
    await _require_trainee(session, org_id, trainee_id)
    await repository.set_trainee_access(session, org_id, trainee_id, revoked_at=now if revoked else None)
    refreshed = await repository.trainee_by_id(session, org_id, trainee_id)
    return _trainee_read(refreshed)  # type: ignore[arg-type]


async def _require_trainee(session: AsyncSession, org_id: uuid.UUID, trainee_id: uuid.UUID) -> Trainee:
    """Fetch a trainee, or refuse the request if this organisation has none by that id."""
    trainee = await repository.trainee_by_id(session, org_id, trainee_id)
    if trainee is None:
        raise errors.TraineeNotFound()
    return trainee


def _trainee_read(trainee: Trainee) -> TraineeRead:
    """Shape a trainee row into what a route may return."""
    return TraineeRead(
        id=trainee.id,
        email=trainee.email,
        first_name=trainee.first_name,
        last_name=trainee.last_name,
        cohort_id=trainee.cohort_id,
        user_id=trainee.user_id,
        access_revoked=trainee.access_revoked_at is not None,
        anonymised=trainee.anonymised_at is not None,
    )


async def read_trainee(session: AsyncSession, org_id: uuid.UUID, trainee_id: uuid.UUID) -> TraineeRead:
    """One roster entry of this organisation, or a refusal if it has none by that id."""
    return _trainee_read(await _require_trainee(session, org_id, trainee_id))


async def ensure_trainee(session: AsyncSession, org_id: uuid.UUID, trainee_id: uuid.UUID) -> None:
    """Confirm this id names a roster entry of this organisation.

    A slot's `trainee_id` is a `users.id` and a decision's is a `trainees.id`; used
    here so a caller mistake reads as a caller error, not a foreign-key 500.
    """
    await _require_trainee(session, org_id, trainee_id)


async def trainee_email(session: AsyncSession, org_id: uuid.UUID, trainee_id: uuid.UUID) -> str:
    """The roster address, not the signed-in account's.

    `user_id` is often null before the person has signed in, so the roster entry's
    address is the only one there is. When both exist they are the same value.
    """
    return (await _require_trainee(session, org_id, trainee_id)).email


async def trainee_ids_for_user(session: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
    """Translate a `users.id` into the `trainees.id` rows for this person.

    A slot addresses a candidate by `users.id`, a decision by `trainees.id`; one
    column name, two meanings.
    """
    return await repository.trainee_ids_for_user(session, user_id)


async def audiences_for_viewer(session: AsyncSession, user_id: uuid.UUID) -> ViewerAudiences:
    """Which rooms this person may see into.

    Bound into `core.audience` (see `bind_viewer_audiences`). Organisations come
    from membership, groups from the roster.
    """
    memberships = await tenancy.memberships_for_token(session, user_id)
    groups = await repository_groups.group_ids_for_user(session, user_id)
    return ViewerAudiences(
        org_ids=frozenset(membership.org_id for membership in memberships),
        group_ids=frozenset(groups),
    )


async def count_trainees(session: AsyncSession, org_id: uuid.UUID) -> int:
    """How many people this organisation teaches."""
    return await repository.count_trainees(session, org_id)


async def trainees_by_user_id(
    session: AsyncSession, org_id: uuid.UUID, user_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, TraineeRead]:
    """Roster entries keyed by user id, for a caller holding slots (which name a `users.id`)."""
    trainees = await repository.trainees_for_users(session, org_id, list(user_ids))
    return {trainee.user_id: _trainee_read(trainee) for trainee in trainees if trainee.user_id is not None}


async def claim_roster_entries(session: AsyncSession, user_id: uuid.UUID, email: str) -> None:
    """Connect a new account to the roster entries already waiting for it, by email."""
    for trainee in await repository.trainees_by_email_everywhere(session, email):
        if trainee.user_id is None:
            await repository.link_trainee_to_user(session, trainee.org_id, trainee.id, user_id=user_id)


async def ensure_rosterable(session: AsyncSession, org_id: uuid.UUID, user_ids: Sequence[uuid.UUID]) -> None:
    """Refuse to put a revoked trainee — or a stranger — on a circuit (R3, SEC-014).

    Called by `sittings` when a circuit is built or somebody is appended to a live
    one; this rule once had no caller, so revoking access did not stop scheduling.

    SEC-014: a `users.id` with no linked trainee row in this organisation is now
    refused. It used to pass — the reasoning was that an org might examine
    somebody it had not rostered — but that let an admin enrol any account id in
    the system into their own circuit, including one that had never been invited
    here. Invited people are rostered (`add_trainee` links a trainee row before
    the invite), so requiring a roster row is the same as requiring membership or
    an explicit invitation. Roster somebody first, then schedule them.
    """
    known = await trainees_by_user_id(session, org_id, list(user_ids))
    for user_id in user_ids:
        trainee = known.get(user_id)
        if trainee is None:
            raise errors.TraineeNotOnRosterError()
        try:
            domain.ensure_rosterable(domain.TraineeState(access_revoked=trainee.access_revoked))
        except domain.TraineeRevoked as exc:
            raise errors.TraineeRevokedError(str(exc)) from exc


# --- Rostering a cohort at once.


async def add_trainees(
    session: AsyncSession, org_id: uuid.UUID, *, entries: list[CreateTrainee], now: datetime
) -> BulkTraineesResult:
    """Add every row that can be added; report every row that cannot.

    Duplicates within the upload are skipped after the first, by normalised
    address, so a spreadsheet with the same person twice does not fail on the second.
    """
    outcome = BulkTraineesResult()
    seen: set[str] = set()
    for entry in entries:
        key = entry.email.strip().lower()
        if key in seen:
            outcome.skipped.append(SkippedTrainee(email=entry.email, code=errors.TraineeExists.code))
            continue
        seen.add(key)
        try:
            created = await add_trainee(
                session,
                org_id,
                email=entry.email,
                first_name=entry.first_name,
                last_name=entry.last_name,
                cohort_id=entry.cohort_id,
                now=now,
            )
        except errors.TraineeExists as exc:
            outcome.skipped.append(SkippedTrainee(email=entry.email, code=exc.code))
            continue
        outcome.created.append(created)
    return outcome
