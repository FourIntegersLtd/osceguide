"""Cohorts, groups, and who a circuit would contain.

A cohort is an academic-year grouping; a trainee group is what a circuit is built
from.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.roster import domain, errors, repository_groups
from app.features.roster.models import Cohort, TraineeGroup
from app.features.roster.schemas import (
    CohortRead,
    GroupRead,
    ResolvedRoster,
    RosterWarningRead,
    UpdateCohort,
)
from app.features.roster.service import _require_trainee

# `academic_year` can be cleared and `name` cannot, so the two are not treated
# alike: an absent key leaves the value alone in both cases.
_COHORT_FIELDS = ("name", "academic_year")


async def add_cohort(
    session: AsyncSession, org_id: uuid.UUID, *, name: str, academic_year: str | None
) -> CohortRead:
    if await repository_groups.cohort_by_name(session, org_id, name) is not None:
        raise errors.CohortExists()
    cohort = await repository_groups.create_cohort(session, org_id, name=name, academic_year=academic_year)
    return _cohort_read(cohort)


async def list_cohorts(session: AsyncSession, org_id: uuid.UUID) -> list[CohortRead]:
    return [_cohort_read(cohort) for cohort in await repository_groups.list_cohorts(session, org_id)]


async def update_cohort(
    session: AsyncSession,
    org_id: uuid.UUID,
    cohort_id: uuid.UUID,
    *,
    body: UpdateCohort,
    fields_sent: set[str],
) -> CohortRead:
    """Rename an intake, or say which academic year it is. Only what was sent is
    written. Renaming the row keeps its trainees; nothing has to be moved.
    """
    cohort = await _require_cohort(session, org_id, cohort_id)
    named = set(_COHORT_FIELDS) & fields_sent
    name = body.name if "name" in named else None
    if name is not None and name != cohort.name:
        # `(org_id, name)` is unique, and the database refuses it, which an
        # administrator reading "internal error" cannot act on.
        taken = await repository_groups.cohort_by_name(session, org_id, name)
        if taken is not None and taken.id != cohort.id:
            raise errors.CohortExists()
    await repository_groups.update_cohort(
        session,
        org_id,
        cohort_id,
        name=name,
        academic_year=body.academic_year if "academic_year" in named else None,
        clear_academic_year="academic_year" in named and body.academic_year is None,
    )
    return _cohort_read(await _require_cohort(session, org_id, cohort_id))


async def delete_cohort(session: AsyncSession, org_id: uuid.UUID, cohort_id: uuid.UUID) -> None:
    """Remove an intake that nothing is attached to any more.

    Refuses while trainees still belong to it. Their `cohort_id` is `SET NULL`, so
    an unrefused delete would silently leave people with no intake instead of
    failing; moving them out is `PATCH /trainees/{id}`, done on purpose.
    """
    await _require_cohort(session, org_id, cohort_id)
    if await repository_groups.count_trainees_in_cohort(session, org_id, cohort_id):
        raise errors.CohortInUse()
    await repository_groups.delete_cohort(session, org_id, cohort_id)


async def add_group(session: AsyncSession, org_id: uuid.UUID, *, label: str) -> GroupRead:
    if await repository_groups.group_by_label(session, org_id, label) is not None:
        raise errors.GroupExists()
    group = await repository_groups.create_group(session, org_id, label=label)
    return GroupRead(id=group.id, label=group.label, member_count=0)


async def list_groups(session: AsyncSession, org_id: uuid.UUID) -> list[GroupRead]:
    return [
        GroupRead(id=group.id, label=group.label, member_count=member_count)
        for group, member_count in await repository_groups.list_groups(session, org_id)
    ]


async def rename_group(
    session: AsyncSession, org_id: uuid.UUID, group_id: uuid.UUID, *, label: str
) -> GroupRead:
    """Rename a group, keeping its members."""
    group = await _require_group(session, org_id, group_id)
    if label != group.label:
        clash = await repository_groups.group_by_label(session, org_id, label)
        if clash is not None and clash.id != group.id:
            raise errors.GroupExists()
        await repository_groups.update_group_label(session, org_id, group_id, label=label)
    return GroupRead(id=group.id, label=label, member_count=await _member_count(session, group_id))


async def delete_group(session: AsyncSession, org_id: uuid.UUID, group_id: uuid.UUID) -> None:
    """Remove a group that nobody is in.

    Refuses while it still has members, so the caller must empty it on purpose
    through `PUT /trainee-groups/{id}/members` before deleting it.
    """
    await _require_group(session, org_id, group_id)
    if await repository_groups.group_member_ids(session, group_id):
        raise errors.GroupNotEmpty()
    await repository_groups.delete_group(session, org_id, group_id)


async def set_group_members(
    session: AsyncSession, org_id: uuid.UUID, group_id: uuid.UUID, *, trainee_ids: list[uuid.UUID]
) -> GroupRead:
    group = await _require_group(session, org_id, group_id)
    for trainee_id in trainee_ids:
        # Checked against this org, so a trainee id from elsewhere cannot be
        # added by guessing one.
        await _require_trainee(session, org_id, trainee_id)
    await repository_groups.set_group_members(session, group_id, trainee_ids=trainee_ids)
    return GroupRead(id=group.id, label=group.label, member_count=await _member_count(session, group_id))


async def resolve_roster(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    trainee_ids: list[uuid.UUID],
    group_ids: list[uuid.UUID],
) -> ResolvedRoster:
    """Who a circuit would contain, resolved before it is built.

    Returned ahead of time so an empty linked group is seen now rather than when
    the examination starts and half the candidates are missing.
    """
    groups: list[domain.GroupRef] = []
    for group_id in group_ids:
        await _require_group(session, org_id, group_id)
        members = await repository_groups.group_member_ids(session, group_id)
        groups.append(
            domain.GroupRef(group_id=str(group_id), members=[str(member_id) for member_id in members])
        )

    resolved, warnings = domain.resolve_roster(
        explicit=[str(trainee_id) for trainee_id in trainee_ids], groups=groups
    )
    return ResolvedRoster(
        trainee_ids=[uuid.UUID(trainee_id) for trainee_id in resolved],
        warnings=[
            RosterWarningRead(code=warning.code, group_id=uuid.UUID(warning.group_id)) for warning in warnings
        ],
    )


async def _member_count(session: AsyncSession, group_id: uuid.UUID) -> int:
    return len(await repository_groups.group_member_ids(session, group_id))


async def _require_group(session: AsyncSession, org_id: uuid.UUID, group_id: uuid.UUID) -> TraineeGroup:
    group = await repository_groups.group_by_id(session, org_id, group_id)
    if group is None:
        raise errors.GroupNotFound()
    return group


async def _require_cohort(session: AsyncSession, org_id: uuid.UUID, cohort_id: uuid.UUID) -> Cohort:
    cohort = await repository_groups.cohort_by_id(session, org_id, cohort_id)
    if cohort is None:
        raise errors.CohortNotFound()
    return cohort


def _cohort_read(cohort: Cohort) -> CohortRead:
    return CohortRead(
        id=cohort.id, name=cohort.name, academic_year=cohort.academic_year, status=cohort.status
    )
