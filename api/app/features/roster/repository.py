"""Storage for the people an organisation teaches. Org-scoped methods take
`org_id` first.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, or_, select, update
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
) -> Trainee:
    """Add a trainee to an organisation's roster."""
    trainee = Trainee(
        org_id=org_id,
        email=normalize_email(email),
        first_name=first_name,
        last_name=last_name,
        cohort_id=cohort_id,
    )
    session.add(trainee)
    await session.flush()
    await session.refresh(trainee)
    return trainee


async def trainee_by_id(session: AsyncSession, org_id: uuid.UUID, trainee_id: uuid.UUID) -> Trainee | None:
    """Find a trainee at this organisation by their roster id."""
    stmt = select(Trainee).where(Trainee.org_id == org_id, Trainee.id == trainee_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def trainee_ids_for_user(session: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
    """Every roster entry this person is, across organisations.

    Not org-scoped on purpose: answers "who am I, as a candidate?" for `/me`
    routes, where there is no organisation in the path.
    """
    stmt = select(Trainee.id).where(Trainee.user_id == user_id)
    return list((await session.execute(stmt)).scalars())


async def trainee_by_email(session: AsyncSession, org_id: uuid.UUID, email: str) -> Trainee | None:
    """Find a trainee at this organisation by their email address."""
    stmt = select(Trainee).where(Trainee.org_id == org_id, Trainee.email == normalize_email(email))
    return (await session.execute(stmt)).scalar_one_or_none()


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
    stmt = select(Trainee).where(Trainee.org_id == org_id)
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
    return await keyset_page(
        session,
        stmt,
        sort_col=Trainee.created_at,
        id_col=Trainee.id,
        limit=limit,
        cursor=cursor,
        descending=False,
    )


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
        update(Trainee).where(Trainee.org_id == org_id, Trainee.id == trainee_id).values(**values)
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


async def link_trainee_to_user(
    session: AsyncSession, org_id: uuid.UUID, trainee_id: uuid.UUID, *, user_id: uuid.UUID
) -> None:
    """Connect a roster entry to the account that just registered for it."""
    await session.execute(
        update(Trainee).where(Trainee.org_id == org_id, Trainee.id == trainee_id).values(user_id=user_id)
    )


async def count_trainees(session: AsyncSession, org_id: uuid.UUID) -> int:
    """How many trainees are on this organisation's roster."""
    stmt = select(func.count()).select_from(Trainee).where(Trainee.org_id == org_id)
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
