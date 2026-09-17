"""Storage for feedback templates: an org's rubrics and their versions.

Split from `repository.py` along the aggregate. Every function takes `org_id`
first and scopes by it, so a template id cannot be probed across tenants.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ownership import owned_by, owner_kind_for
from app.features.rubrics.models import FeedbackTemplate, FeedbackTemplateVersion


async def create_feedback_template(
    session: AsyncSession, org_id: uuid.UUID | None, *, rubric_version_id: uuid.UUID, title: str
) -> FeedbackTemplate:
    row = FeedbackTemplate(
        owner_kind=owner_kind_for(org_id), org_id=org_id, rubric_version_id=rubric_version_id, title=title
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def feedback_template_by_id(
    session: AsyncSession, org_id: uuid.UUID | None, template_id: uuid.UUID
) -> FeedbackTemplate | None:
    stmt = select(FeedbackTemplate).where(
        owned_by(FeedbackTemplate, org_id), FeedbackTemplate.id == template_id
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def feedback_templates_for_org(
    session: AsyncSession, org_id: uuid.UUID | None
) -> list[FeedbackTemplate]:
    stmt = (
        select(FeedbackTemplate)
        .where(owned_by(FeedbackTemplate, org_id))
        .order_by(FeedbackTemplate.created_at, FeedbackTemplate.id)
    )
    return list((await session.execute(stmt)).scalars())


async def feedback_template_versions(
    session: AsyncSession, org_id: uuid.UUID | None, template_id: uuid.UUID
) -> list[FeedbackTemplateVersion]:
    stmt = (
        select(FeedbackTemplateVersion)
        .where(
            owned_by(FeedbackTemplateVersion, org_id),
            FeedbackTemplateVersion.template_id == template_id,
        )
        .order_by(FeedbackTemplateVersion.version)
    )
    return list((await session.execute(stmt)).scalars())


async def feedback_template_version(
    session: AsyncSession, org_id: uuid.UUID | None, version_id: uuid.UUID
) -> FeedbackTemplateVersion | None:
    """One of this org's feedback template versions, scoped to it."""
    stmt = select(FeedbackTemplateVersion).where(
        owned_by(FeedbackTemplateVersion, org_id),
        FeedbackTemplateVersion.id == version_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def add_feedback_template_version(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    *,
    template_id: uuid.UUID,
    version: int,
    field_selection: dict[str, Any],
) -> FeedbackTemplateVersion:
    row = FeedbackTemplateVersion(
        owner_kind=owner_kind_for(org_id),
        org_id=org_id,
        template_id=template_id,
        version=version,
        field_selection=field_selection,
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def set_feedback_template_version_selection(
    session: AsyncSession, org_id: uuid.UUID | None, version_id: uuid.UUID, *, field_selection: dict[str, Any]
) -> None:
    await session.execute(
        update(FeedbackTemplateVersion)
        .where(owned_by(FeedbackTemplateVersion, org_id), FeedbackTemplateVersion.id == version_id)
        .values(field_selection=field_selection)
    )


async def set_feedback_template_version_status(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    version_id: uuid.UUID,
    *,
    status: str,
    at: datetime,
    by: uuid.UUID | None,
) -> None:
    values: dict[str, Any] = {"status": status}
    if status == "published":
        values.update(published_at=at, published_by=by)
    elif status == "archived":
        values.update(archived_at=at, archived_by=by)
    await session.execute(
        update(FeedbackTemplateVersion)
        .where(owned_by(FeedbackTemplateVersion, org_id), FeedbackTemplateVersion.id == version_id)
        .values(**values)
    )


async def count_published_versions(session: AsyncSession, org_id: uuid.UUID | None) -> int:
    """How many rubrics this org could actually bind a sitting to."""
    stmt = (
        select(func.count())
        .select_from(FeedbackTemplateVersion)
        .where(
            owned_by(FeedbackTemplateVersion, org_id),
            FeedbackTemplateVersion.status == "published",
        )
    )
    return int((await session.execute(stmt)).scalar_one())
