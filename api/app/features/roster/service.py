"""Roster use cases."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audience import ViewerAudiences
from app.features.identity import service as identity
from app.features.identity import service_invitations as invitations
from app.features.roster import domain, errors, repository, repository_groups
from app.features.roster.models import Trainee
from app.features.roster.schemas import (
    TraineeRead,
)
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
    if await repository.trainee_by_email(session, org_id, email) is not None:
        raise errors.TraineeExists()
    row = await repository.create_trainee(
        session,
        org_id,
        email=email,
        first_name=first_name,
        last_name=last_name,
        cohort_id=cohort_id,
    )
    # An institution usually rosters people who already have an account. The
    # link was modelled and nothing ever made it: `user_id` stayed null for
    # every trainee ever added, so a slot (which names a `users.id`) could not
    # be traced back to the roster entry that carries the person's name.
    #
    # Somebody with no account is invited, and linked now. A slot names a
    # `users.id`, so a trainee without one could be rostered and never
    # scheduled; the invitation is what turns a spreadsheet row into a
    # candidate who can sit.
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
    await repository.link_trainee_to_user(session, org_id, row.id, user_id=existing.id)
    await session.refresh(row)
    return _trainee_read(row)


def _display_name(first: str | None, last: str | None, email: str) -> str:
    return " ".join(part for part in (first, last) if part) or email


async def list_trainees(
    session: AsyncSession, org_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None
) -> tuple[list[TraineeRead], str | None]:
    rows, next_cursor = await repository.list_trainees(session, org_id, limit=limit, cursor=cursor)
    return [_trainee_read(r) for r in rows], next_cursor


async def set_access(
    session: AsyncSession,
    org_id: uuid.UUID,
    trainee_id: uuid.UUID,
    *,
    revoked: bool,
    now: datetime,
) -> TraineeRead:
    await _require_trainee(session, org_id, trainee_id)
    await repository.set_trainee_access(session, org_id, trainee_id, revoked_at=now if revoked else None)
    refreshed = await repository.trainee_by_id(session, org_id, trainee_id)
    return _trainee_read(refreshed)  # type: ignore[arg-type]


async def _require_trainee(session: AsyncSession, org_id: uuid.UUID, trainee_id: uuid.UUID) -> Trainee:
    row = await repository.trainee_by_id(session, org_id, trainee_id)
    if row is None:
        raise errors.TraineeNotFound()
    return row


def _trainee_read(row: Trainee) -> TraineeRead:
    return TraineeRead(
        id=row.id,
        email=row.email,
        first_name=row.first_name,
        last_name=row.last_name,
        cohort_id=row.cohort_id,
        user_id=row.user_id,
        access_revoked=row.access_revoked_at is not None,
        anonymised=row.anonymised_at is not None,
    )


async def ensure_trainee(session: AsyncSession, org_id: uuid.UUID, trainee_id: uuid.UUID) -> None:
    """That this id names a roster entry of this organisation.

    `results` asks before writing a decision. A slot's `trainee_id` is a
    `users.id` and a decision's is a `trainees.id`, so an id taken from the
    circuit console and used on the decision route reaches the database and
    fails a foreign key, which surfaces as a 500. That is a caller mistake and
    should read as one.
    """
    await _require_trainee(session, org_id, trainee_id)


async def trainee_email(session: AsyncSession, org_id: uuid.UUID, trainee_id: uuid.UUID) -> str:
    """Where to write to this candidate.

    The roster address, not the signed-in account's: an institution rosters
    people before they have ever signed in, so `user_id` is often null and the
    address on the roster entry is the only one there is. When both exist they
    are the same value — registering claims the entry by email.

    `results` asks for this so that releasing an outcome writes to the
    candidate. It used to send to the administrator who pressed the button,
    who is the one person already looking at the result.
    """
    return (await _require_trainee(session, org_id, trainee_id)).email


async def trainee_ids_for_user(session: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
    """Which roster entries this signed-in person is.

    `results` addresses a candidate by `trainees.id` while a slot addresses
    them by `users.id`; one column name, two meanings. This is the translation,
    and it lives here because `roster` owns the trainee.
    """
    return await repository.trainee_ids_for_user(session, user_id)


async def audiences_for_viewer(session: AsyncSession, user_id: uuid.UUID) -> ViewerAudiences:
    """Which rooms this person may see into.

    Bound into `core.audience` by `main.py`: `community`, `marketplace` and
    `peer_practice` all need this and all sit below the two slices that know
    the answer. Organisations come from membership, groups from the roster.
    """
    memberships = await tenancy.memberships_for_token(session, user_id)
    groups = await repository_groups.group_ids_for_user(session, user_id)
    return ViewerAudiences(
        org_ids=frozenset(m.org_id for m in memberships),
        group_ids=frozenset(groups),
    )


async def count_trainees(session: AsyncSession, org_id: uuid.UUID) -> int:
    """How many people this organisation teaches.

    A count, not a list: the org dashboard reads four of these and the legacy
    screen fetched four whole collections to call `.length` on them.
    """
    return await repository.count_trainees(session, org_id)


async def trainees_by_user_id(
    session: AsyncSession, org_id: uuid.UUID, user_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, TraineeRead]:
    """Roster entries keyed by the user id a slot names them with.

    A slot's `trainee_id` is a `users.id`; the name to show beside it lives on
    `trainees`. Keyed by user id so a caller holding slots can look straight up.
    """
    rows = await repository.trainees_for_users(session, org_id, list(user_ids))
    return {row.user_id: _trainee_read(row) for row in rows if row.user_id is not None}


async def claim_roster_entries(session: AsyncSession, user_id: uuid.UUID, email: str) -> None:
    """Connect a new account to the roster entries already waiting for it.

    Bound into `identity.register` by `main.py`: an institution adds somebody by
    email long before they sign up, and until this ran the two records never
    met — the person appeared on a slot with no name, and their released
    results, which are keyed on `trainees.id`, were unreachable.
    """
    for row in await repository.trainees_by_email_everywhere(session, email):
        if row.user_id is None:
            await repository.link_trainee_to_user(session, row.org_id, row.id, user_id=user_id)


async def ensure_rosterable(session: AsyncSession, org_id: uuid.UUID, user_ids: Sequence[uuid.UUID]) -> None:
    """Refuse to put a revoked trainee on a circuit (R3).

    Called by `sittings` when a circuit is built or somebody is appended to a
    live one. The rule was written and unit-tested and had no caller, so
    revoking a trainee's access stopped them signing in and did not stop them
    being scheduled into an examination — and a slot they cannot reach is a
    candidate marked absent.

    People not on the roster at all are not refused here: a slot names a user,
    and an organisation may examine somebody it has not rostered.
    """
    known = await trainees_by_user_id(session, org_id, list(user_ids))
    for user_id in user_ids:
        trainee = known.get(user_id)
        if trainee is None:
            continue
        try:
            domain.ensure_rosterable(domain.TraineeState(access_revoked=trainee.access_revoked))
        except domain.TraineeRevoked as exc:
            raise errors.TraineeRevokedError(str(exc)) from exc
