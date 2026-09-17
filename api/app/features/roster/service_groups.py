"""Cohorts, groups, and who a circuit would contain.

Split from `service.py` along the aggregate: that module is about a person on
the roster, this one about the ways an institution divides them up. A cohort
is an academic-year grouping; a trainee group is what a circuit is built from,
and its membership is a table rather than b2b's lowercased label match.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.roster import domain, errors, repository
from app.features.roster.models import Cohort, TraineeGroup
from app.features.roster.schemas import (
    CohortRead,
    GroupRead,
    ResolvedRoster,
    RosterWarningRead,
)
from app.features.roster.service import _require_trainee


async def add_cohort(
    session: AsyncSession, org_id: uuid.UUID, *, name: str, academic_year: str | None
) -> CohortRead:
    row = await repository.create_cohort(session, org_id, name=name, academic_year=academic_year)
    return _cohort_read(row)


async def list_cohorts(session: AsyncSession, org_id: uuid.UUID) -> list[CohortRead]:
    return [_cohort_read(r) for r in await repository.list_cohorts(session, org_id)]


async def add_group(session: AsyncSession, org_id: uuid.UUID, *, label: str) -> GroupRead:
    if await repository.group_by_label(session, org_id, label) is not None:
        raise errors.GroupExists()
    row = await repository.create_group(session, org_id, label=label)
    return GroupRead(id=row.id, label=row.label, member_count=0)


async def list_groups(session: AsyncSession, org_id: uuid.UUID) -> list[GroupRead]:
    return [
        GroupRead(id=g.id, label=g.label, member_count=count)
        for g, count in await repository.list_groups(session, org_id)
    ]


async def set_group_members(
    session: AsyncSession, org_id: uuid.UUID, group_id: uuid.UUID, *, trainee_ids: list[uuid.UUID]
) -> GroupRead:
    group = await _require_group(session, org_id, group_id)
    for trainee_id in trainee_ids:
        # Checked against this org, so a trainee id from elsewhere cannot be
        # added by guessing one.
        await _require_trainee(session, org_id, trainee_id)
    await repository.set_group_members(session, group_id, trainee_ids=trainee_ids)
    members = await repository.group_member_ids(session, group_id)
    return GroupRead(id=group.id, label=group.label, member_count=len(members))


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
        members = await repository.group_member_ids(session, group_id)
        groups.append(domain.GroupRef(group_id=str(group_id), members=[str(m) for m in members]))

    resolved, warnings = domain.resolve_roster(explicit=[str(t) for t in trainee_ids], groups=groups)
    return ResolvedRoster(
        trainee_ids=[uuid.UUID(t) for t in resolved],
        warnings=[RosterWarningRead(code=w.code, group_id=uuid.UUID(w.group_id)) for w in warnings],
    )


async def _require_group(session: AsyncSession, org_id: uuid.UUID, group_id: uuid.UUID) -> TraineeGroup:
    row = await repository.group_by_id(session, org_id, group_id)
    if row is None:
        raise errors.GroupNotFound()
    return row


def _cohort_read(row: Cohort) -> CohortRead:
    return CohortRead(id=row.id, name=row.name, academic_year=row.academic_year, status=row.status)
