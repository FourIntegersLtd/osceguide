"""Storage for the ways an institution divides its trainees up: cohorts and
groups. Org-scoped methods take `org_id` first.
"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.roster.domain import normalize_label
from app.features.roster.models import Cohort, Trainee, TraineeGroup, TraineeGroupMember

# --- cohorts ---------------------------------------------------------------


async def create_cohort(
    session: AsyncSession, org_id: uuid.UUID, *, name: str, academic_year: str | None
) -> Cohort:
    """Create a new intake for an organisation."""
    cohort = Cohort(org_id=org_id, name=name, academic_year=academic_year, status="active")
    session.add(cohort)
    await session.flush()
    await session.refresh(cohort)
    return cohort


async def list_cohorts(session: AsyncSession, org_id: uuid.UUID) -> list[Cohort]:
    """Every cohort at an organisation, alphabetically."""
    stmt = select(Cohort).where(Cohort.org_id == org_id).order_by(Cohort.name)
    return list((await session.execute(stmt)).scalars())


async def cohort_by_id(session: AsyncSession, org_id: uuid.UUID, cohort_id: uuid.UUID) -> Cohort | None:
    """Find a cohort at this organisation by id."""
    stmt = select(Cohort).where(Cohort.org_id == org_id, Cohort.id == cohort_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def cohort_by_name(session: AsyncSession, org_id: uuid.UUID, name: str) -> Cohort | None:
    """The cohort this name already belongs to, if any.

    Asked before a rename because `(org_id, name)` is unique in the database,
    and an insert or update that collides with it surfaces as a 500 rather than
    as the 409 that says what to do about it.
    """
    stmt = select(Cohort).where(Cohort.org_id == org_id, Cohort.name == name)
    return (await session.execute(stmt)).scalar_one_or_none()


async def update_cohort(
    session: AsyncSession,
    org_id: uuid.UUID,
    cohort_id: uuid.UUID,
    *,
    name: str | None,
    academic_year: str | None,
    clear_academic_year: bool,
) -> None:
    """Write only what was sent; a null academic year clears it, a null name does not."""
    values: dict[str, object] = {}
    if name is not None:
        values["name"] = name
    if clear_academic_year:
        values["academic_year"] = None
    elif academic_year is not None:
        values["academic_year"] = academic_year
    if not values:
        return
    await session.execute(
        update(Cohort).where(Cohort.org_id == org_id, Cohort.id == cohort_id).values(**values)
    )


async def delete_cohort(session: AsyncSession, org_id: uuid.UUID, cohort_id: uuid.UUID) -> None:
    """Remove a cohort. Its trainees' `cohort_id` is set to null by the database."""
    await session.execute(delete(Cohort).where(Cohort.org_id == org_id, Cohort.id == cohort_id))


async def count_trainees_in_cohort(session: AsyncSession, org_id: uuid.UUID, cohort_id: uuid.UUID) -> int:
    """How many people this intake is still the intake of.

    A count rather than a list, and read before the delete: a cohort's
    `trainees.cohort_id` points here with `SET NULL`, so removing it without
    asking would quietly leave a year group of people belonging to nothing.
    """
    stmt = (
        select(func.count())
        .select_from(Trainee)
        .where(Trainee.org_id == org_id, Trainee.cohort_id == cohort_id)
    )
    return int((await session.execute(stmt)).scalar_one())


# --- groups ----------------------------------------------------------------


async def create_group(session: AsyncSession, org_id: uuid.UUID, *, label: str) -> TraineeGroup:
    """Create a new, empty group at an organisation."""
    group = TraineeGroup(org_id=org_id, label=label, label_normalized=normalize_label(label))
    session.add(group)
    await session.flush()
    await session.refresh(group)
    return group


async def group_by_id(session: AsyncSession, org_id: uuid.UUID, group_id: uuid.UUID) -> TraineeGroup | None:
    """Find a group at this organisation by id."""
    stmt = select(TraineeGroup).where(TraineeGroup.org_id == org_id, TraineeGroup.id == group_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def group_by_label(session: AsyncSession, org_id: uuid.UUID, label: str) -> TraineeGroup | None:
    """Find a group at this organisation by its label, ignoring case and spacing."""
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
    return [(group, member_count) for group, member_count in (await session.execute(stmt)).all()]


async def update_group_label(
    session: AsyncSession, org_id: uuid.UUID, group_id: uuid.UUID, *, label: str
) -> None:
    """Rename, and move the normalised form with it.

    Both columns or neither: `label_normalized` is what the unique constraint
    and every membership lookup read, so a rename that updated only the label
    would leave the group findable under its old name and unfindable under its
    new one.
    """
    await session.execute(
        update(TraineeGroup)
        .where(TraineeGroup.org_id == org_id, TraineeGroup.id == group_id)
        .values(label=label, label_normalized=normalize_label(label))
    )


async def delete_group(session: AsyncSession, org_id: uuid.UUID, group_id: uuid.UUID) -> None:
    """Remove a group. Callers check it is empty first (`GroupNotEmpty`)."""
    await session.execute(
        delete(TraineeGroup).where(TraineeGroup.org_id == org_id, TraineeGroup.id == group_id)
    )


async def set_group_members(
    session: AsyncSession, group_id: uuid.UUID, *, trainee_ids: list[uuid.UUID]
) -> None:
    """Replace the membership wholesale.

    A set rather than an add: the caller is stating who is in the group, and a
    partial update would leave whoever they removed still in it.
    """
    await session.execute(delete(TraineeGroupMember).where(TraineeGroupMember.group_id == group_id))
    session.add_all(
        [
            TraineeGroupMember(group_id=group_id, trainee_id=trainee_id)
            for trainee_id in dict.fromkeys(trainee_ids)
        ]
    )
    await session.flush()


async def group_member_ids(session: AsyncSession, group_id: uuid.UUID) -> list[uuid.UUID]:
    """The trainees in a group, oldest member first."""
    stmt = (
        select(TraineeGroupMember.trainee_id)
        .join(Trainee, Trainee.id == TraineeGroupMember.trainee_id)
        .where(TraineeGroupMember.group_id == group_id)
        .order_by(Trainee.created_at)
    )
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
