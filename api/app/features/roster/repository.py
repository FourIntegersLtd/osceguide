"""Storage for trainees, cohorts and groups. Org-scoped methods take org_id first."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import keyset_page
from app.features.roster.domain import normalize_email, normalize_label
from app.features.roster.models import Cohort, Trainee, TraineeGroup, TraineeGroupMember


async def create_trainee(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    email: str,
    first_name: str | None,
    last_name: str | None,
    cohort_id: uuid.UUID | None,
) -> Trainee:
    row = Trainee(
        org_id=org_id,
        email=normalize_email(email),
        first_name=first_name,
        last_name=last_name,
        cohort_id=cohort_id,
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def trainee_by_id(session: AsyncSession, org_id: uuid.UUID, trainee_id: uuid.UUID) -> Trainee | None:
    stmt = select(Trainee).where(Trainee.org_id == org_id, Trainee.id == trainee_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def trainee_ids_for_user(session: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
    """Every roster entry this person is, across organisations.

    Not org-scoped on purpose: it answers "who am I, as a candidate?" for
    `/me` routes, where there is no organisation in the path. A person can be
    on more than one institution's roster.
    """
    stmt = select(Trainee.id).where(Trainee.user_id == user_id)
    return list((await session.execute(stmt)).scalars())


async def group_ids_for_user(session: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
    """Every teaching group this person is currently in, across organisations.

    Revoked trainees are excluded: somebody whose access an institution has
    withdrawn stops seeing that institution's rooms. What they posted while
    they were a member stays where it is — the group would otherwise lose half
    a conversation when one person leaves.
    """
    stmt = (
        select(TraineeGroupMember.group_id)
        .join(Trainee, Trainee.id == TraineeGroupMember.trainee_id)
        .where(Trainee.user_id == user_id, Trainee.access_revoked_at.is_(None))
    )
    return list((await session.execute(stmt)).scalars())


async def trainee_by_email(session: AsyncSession, org_id: uuid.UUID, email: str) -> Trainee | None:
    stmt = select(Trainee).where(Trainee.org_id == org_id, Trainee.email == normalize_email(email))
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_trainees(
    session: AsyncSession, org_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None = None
) -> tuple[list[Trainee], str | None]:
    stmt = select(Trainee).where(Trainee.org_id == org_id)
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
    await session.execute(
        update(Trainee)
        .where(Trainee.org_id == org_id, Trainee.id == trainee_id)
        .values(access_revoked_at=revoked_at)
    )


async def link_trainee_to_user(
    session: AsyncSession, org_id: uuid.UUID, trainee_id: uuid.UUID, *, user_id: uuid.UUID
) -> None:
    await session.execute(
        update(Trainee).where(Trainee.org_id == org_id, Trainee.id == trainee_id).values(user_id=user_id)
    )


# --- cohorts ---------------------------------------------------------------


async def create_cohort(
    session: AsyncSession, org_id: uuid.UUID, *, name: str, academic_year: str | None
) -> Cohort:
    row = Cohort(org_id=org_id, name=name, academic_year=academic_year, status="active")
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def list_cohorts(session: AsyncSession, org_id: uuid.UUID) -> list[Cohort]:
    stmt = select(Cohort).where(Cohort.org_id == org_id).order_by(Cohort.name)
    return list((await session.execute(stmt)).scalars())


# --- groups ----------------------------------------------------------------


async def create_group(session: AsyncSession, org_id: uuid.UUID, *, label: str) -> TraineeGroup:
    row = TraineeGroup(org_id=org_id, label=label, label_normalized=normalize_label(label))
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def group_by_id(session: AsyncSession, org_id: uuid.UUID, group_id: uuid.UUID) -> TraineeGroup | None:
    stmt = select(TraineeGroup).where(TraineeGroup.org_id == org_id, TraineeGroup.id == group_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def group_by_label(session: AsyncSession, org_id: uuid.UUID, label: str) -> TraineeGroup | None:
    stmt = select(TraineeGroup).where(
        TraineeGroup.org_id == org_id, TraineeGroup.label_normalized == normalize_label(label)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_groups(session: AsyncSession, org_id: uuid.UUID) -> list[tuple[TraineeGroup, int]]:
    """Groups with their member counts, in one query rather than one per group."""
    stmt = (
        select(TraineeGroup, func.count(TraineeGroupMember.id))
        .outerjoin(TraineeGroupMember, TraineeGroupMember.group_id == TraineeGroup.id)
        .where(TraineeGroup.org_id == org_id)
        .group_by(TraineeGroup.id)
        .order_by(TraineeGroup.label)
    )
    return [(row[0], row[1]) for row in (await session.execute(stmt)).all()]


async def set_group_members(
    session: AsyncSession, group_id: uuid.UUID, *, trainee_ids: list[uuid.UUID]
) -> None:
    """Replace the membership wholesale.

    A set rather than an add: the caller is stating who is in the group, and a
    partial update would leave whoever they removed still in it.
    """
    await session.execute(delete(TraineeGroupMember).where(TraineeGroupMember.group_id == group_id))
    session.add_all([TraineeGroupMember(group_id=group_id, trainee_id=t) for t in dict.fromkeys(trainee_ids)])
    await session.flush()


async def group_member_ids(session: AsyncSession, group_id: uuid.UUID) -> list[uuid.UUID]:
    stmt = (
        select(TraineeGroupMember.trainee_id)
        .join(Trainee, Trainee.id == TraineeGroupMember.trainee_id)
        .where(TraineeGroupMember.group_id == group_id)
        .order_by(Trainee.created_at)
    )
    return list((await session.execute(stmt)).scalars())


async def count_trainees(session: AsyncSession, org_id: uuid.UUID) -> int:
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

    Deliberately not org-scoped: this answers "who has already been expecting
    this person?" at the moment they register, and more than one institution
    may have.
    """
    stmt = select(Trainee).where(Trainee.email == normalize_email(email))
    return list((await session.execute(stmt)).scalars())
