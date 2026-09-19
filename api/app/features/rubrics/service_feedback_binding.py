"""What another slice may bind a feedback template to.

Split from `service_feedback.py` at the file cap, along the line that was
already there: that module is authoring — creating, editing and publishing a
template — and this is the two questions asked from outside it. A sitting
binds a published version, and a dashboard counts how many an owner has.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.rubrics import errors
from app.features.rubrics import repository_feedback as repository
from app.features.rubrics.models import FeedbackTemplateVersion


async def published_feedback_template(
    session: AsyncSession, org_id: uuid.UUID | None, version_id: uuid.UUID
) -> FeedbackTemplateVersion:
    """The feedback template version a sitting may bind (S1).

    Raises if it is missing, belongs to another org, or is still a draft. The
    NOT NULL foreign key on `sittings` made this look enforced, but a foreign
    key only says the row exists — a sitting could bind a rubric somebody was
    still editing, and candidates would be marked against it.
    """
    row = await repository.feedback_template_version(session, org_id, version_id)
    if row is None:
        raise errors.TemplateVersionNotFound()
    if row.status != "published":
        raise errors.FeedbackTemplateNotPublished("A sitting needs a published feedback template version.")
    return row


async def count_published_versions(session: AsyncSession, org_id: uuid.UUID | None) -> int:
    """How many published feedback templates an owner has; a sitting needs one."""
    return await repository.count_published_versions(session, org_id)
