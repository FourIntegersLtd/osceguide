"""Storage for the people an organisation teaches. Org-scoped methods take
`org_id` first.
"""

from __future__ import annotations

import uuid
from collections.abc import Collection, Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import Select, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import keyset_page
from app.core.search import contains_text
from app.features.roster.domain import normalize_email
from app.features.roster.models import Cohort, Trainee


async def create_trainee(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    email: str,
    first_name: str | None,
    last_name: str | None,
    cohort_id: uuid.UUID | None,
) -> Trainee | None:
    """Add a trainee to an organisation's roster, or None when that address is already on it.

    One statement decides: a duplicate leaves no failed flush behind, so a bulk import
    can carry on to its next row.
    """
    stmt = (
        insert(Trainee)
        .values(
            org_id=org_id,
            email=normalize_email(email),
            first_name=first_name,
            last_name=last_name,
            cohort_id=cohort_id,
        )
        .on_conflict_do_nothing(constraint="uq_trainees_org_email")
        .returning(Trainee)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def trainees_by_ids(
    session: AsyncSession, org_id: uuid.UUID, trainee_ids: Collection[uuid.UUID]
) -> dict[uuid.UUID, Trainee]:
    """The trainees at this organisation with these roster ids, keyed by id; unknown ids are absent."""
    if not trainee_ids:
        return {}
    stmt = select(Trainee).where(Trainee.org_id == org_id, Trainee.id.in_(list(trainee_ids)))
    return {trainee.id: trainee for trainee in (await session.execute(stmt)).scalars()}


async def trainee_by_email(session: AsyncSession, org_id: uuid.UUID, email: str) -> Trainee | None:
    """Find a trainee at this organisation by their email address."""
    stmt = select(Trainee).where(Trainee.org_id == org_id, Trainee.email == normalize_email(email))
    return (await session.execute(stmt)).scalar_one_or_none()


async def trainee_by_id(session: AsyncSession, org_id: uuid.UUID, trainee_id: uuid.UUID) -> Trainee | None:
    """Find a trainee at this organisation by their roster id."""
    stmt = select(Trainee).where(Trainee.org_id == org_id, Trainee.id == trainee_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def follow_account_email(session: AsyncSession, user_id: uuid.UUID, email: str) -> None:
    """Give every roster entry that is this person their new address, except where the same
    organisation already rosters that address for someone else (the unique key would refuse it)."""
    taken = select(Trainee.org_id).where(Trainee.email == email).scalar_subquery()
    await session.execute(
        update(Trainee)
        .where(Trainee.user_id == user_id, Trainee.anonymised_at.is_(None), Trainee.org_id.not_in(taken))
        .values(email=email)
    )


async def trainee_ids_for_user(session: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
    """Every roster entry this person is, across organisations.

    Not org-scoped on purpose: answers "who am I, as a candidate?" for `/me`
    routes, where there is no organisation in the path.
    """
    stmt = select(Trainee.id).where(Trainee.user_id == user_id)
    return list((await session.execute(stmt)).scalars())


def _matching(
    stmt: Select[Any], org_id: uuid.UUID, search: str | None, access_revoked: bool | None
) -> Select[Any]:
    """Narrow a select over trainees to one organisation, a search term and an access state."""
    stmt = stmt.where(Trainee.org_id == org_id)
    if access_revoked is not None:
        stmt = stmt.where(
            Trainee.access_revoked_at.is_not(None) if access_revoked else Trainee.access_revoked_at.is_(None)
        )
    term = (search or "").strip()
    if term:
        stmt = stmt.outerjoin(Cohort, Trainee.cohort_id == Cohort.id).where(
            or_(
                contains_text(Trainee.first_name, term),
                contains_text(Trainee.last_name, term),
                contains_text(Trainee.email, term),
                contains_text(Cohort.name, term),
            )
        )
    return stmt


async def list_trainees(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    limit: int,
    cursor: dict[str, Any] | None = None,
    search: str | None = None,
    access_revoked: bool | None = None,
) -> tuple[list[Trainee], str | None]:
    """A page of an organisation's roster, oldest trainee first.

    `access_revoked`, if given, keeps only trainees whose access is revoked
    (`True`) or still live (`False`).

    `search`, if given, narrows to a trainee whose name, email or cohort name
    contains it, case-insensitively. A left join to `cohorts` so a trainee with
    no cohort is still searchable on name and email.
    """
    stmt = _matching(select(Trainee), org_id, search, access_revoked)
    return await keyset_page(
        session,
        stmt,
        sort_col=Trainee.created_at,
        id_col=Trainee.id,
        limit=limit,
        cursor=cursor,
        descending=False,
    )


async def revoked_org_ids_for_user(session: AsyncSession, user_id: uuid.UUID) -> set[uuid.UUID]:
    """Organisations where every roster entry of this person is revoked (one live entry keeps access)."""
    stmt = (
        select(Trainee.org_id)
        .where(Trainee.user_id == user_id)
        .group_by(Trainee.org_id)
        .having(func.count(Trainee.id) == func.count(Trainee.access_revoked_at))
    )
    return set((await session.execute(stmt)).scalars())


async def set_trainee_access(
    session: AsyncSession, org_id: uuid.UUID, trainee_id: uuid.UUID, *, revoked_at: datetime | None
) -> None:
    """Revoke a trainee's access (a timestamp) or restore it (`None`)."""
    await session.execute(
        update(Trainee)
        .where(Trainee.org_id == org_id, Trainee.id == trainee_id)
        .values(access_revoked_at=revoked_at)
    )


async def update_trainee(
    session: AsyncSession,
    org_id: uuid.UUID,
    trainee_id: uuid.UUID,
    *,
    first_name: str | None,
    last_name: str | None,
    cohort_id: uuid.UUID | None,
    clear_first_name: bool,
    clear_last_name: bool,
    clear_cohort: bool,
) -> None:
    """Write only what the caller sent.

    A null means "clear it", an absent key means "leave it alone"; each field
    carries its own clear flag so the two cannot be collapsed into one.
    """
    values: dict[str, Any] = {}
    if clear_first_name:
        values["first_name"] = None
    elif first_name is not None:
        values["first_name"] = first_name
    if clear_last_name:
        values["last_name"] = None
    elif last_name is not None:
        values["last_name"] = last_name
    if clear_cohort:
        values["cohort_id"] = None
    elif cohort_id is not None:
        values["cohort_id"] = cohort_id
    if not values:
        return
    await session.execute(
        update(Trainee)
        .where(Trainee.org_id == org_id, Trainee.id == trainee_id)
        .values(**values, revision=Trainee.revision + 1)
    )


async def delete_trainee(session: AsyncSession, org_id: uuid.UUID, trainee_id: uuid.UUID) -> None:
    """Delete the row and flush, so `candidate_result_revisions.trainee_id`'s
    `RESTRICT` fails here rather than at some later, unrelated flush."""
    await session.execute(delete(Trainee).where(Trainee.org_id == org_id, Trainee.id == trainee_id))
    await session.flush()


async def anonymise_trainee(
    session: AsyncSession, org_id: uuid.UUID, trainee_id: uuid.UUID, *, email: str, at: datetime
) -> None:
    """Scrub the address and the name; leave everything a decision hangs off.

    `email` is generated by the caller (`f"anon-{trainee_id}@…"`), unique by
    construction so it never collides with `uq_trainees_org_email`.
    """
    await session.execute(
        update(Trainee)
        .where(Trainee.org_id == org_id, Trainee.id == trainee_id)
        .values(email=email, first_name=None, last_name=None, access_revoked_at=at, anonymised_at=at)
    )


async def emails_for_user(session: AsyncSession, user_id: uuid.UUID) -> list[str]:
    """The address on every roster entry this account owns: where an institution's mail goes."""
    stmt = select(Trainee.email).where(Trainee.user_id == user_id)
    return list((await session.execute(stmt)).scalars())


async def anonymise_for_user(session: AsyncSession, user_id: uuid.UUID, *, at: datetime) -> int:
    """Scrub the name and address off every roster entry this account owns, keeping the rows.

    The address becomes `anon-<id>@anonymised.invalid`, unique by construction, as in
    `anonymise_trainee`. Returns how many entries changed.
    """
    result = await session.execute(
        update(Trainee)
        .where(Trainee.user_id == user_id, Trainee.anonymised_at.is_(None))
        .values(
            email=func.concat("anon-", Trainee.id, "@anonymised.invalid"),
            first_name=None,
            last_name=None,
            access_revoked_at=at,
            anonymised_at=at,
        )
    )
    return int(result.rowcount or 0)  # type: ignore[attr-defined]


async def link_trainee_to_user(
    session: AsyncSession, org_id: uuid.UUID, trainee_id: uuid.UUID, *, user_id: uuid.UUID
) -> None:
    """Connect a roster entry to the account that just registered for it."""
    await session.execute(
        update(Trainee).where(Trainee.org_id == org_id, Trainee.id == trainee_id).values(user_id=user_id)
    )


async def count_trainees(
    session: AsyncSession, org_id: uuid.UUID, *, search: str | None = None, access_revoked: bool | None = None
) -> int:
    """How many trainees are on this roster; with filters, how many `list_trainees` pages through."""
    stmt = _matching(select(func.count(Trainee.id)), org_id, search, access_revoked)
    return int((await session.execute(stmt)).scalar_one())


async def trainees_for_users(
    session: AsyncSession, org_id: uuid.UUID, user_ids: Sequence[uuid.UUID]
) -> list[Trainee]:
    """The roster entries for a set of signed-in people, in one query."""
    if not user_ids:
        return []
    stmt = select(Trainee).where(Trainee.org_id == org_id, Trainee.user_id.in_(list(user_ids)))
    return list((await session.execute(stmt)).scalars())


async def trainees_by_email_everywhere(session: AsyncSession, email: str) -> list[Trainee]:
    """Every organisation's roster entry for this address.

    Deliberately not org-scoped: answers "who has already been expecting this
    person?" at the moment they register.
    """
    stmt = select(Trainee).where(Trainee.email == normalize_email(email))
    return list((await session.execute(stmt)).scalars())
