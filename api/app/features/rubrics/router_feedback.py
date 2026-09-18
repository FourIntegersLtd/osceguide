"""Feedback template routes: the rubric a sitting binds and reviewers score with.

A router of its own rather than more of `router.py`, along the same seam the
services take: a rubric is the marking scheme, a feedback template is one set
of reviewers' view of it, and the two are authored at different times.

Both doors again — `/platform/...` and `/orgs/{org_slug}/...` — because the
platform narrows its own rubrics for its own reviewers exactly as an
institution does.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import Forbidden, error_responses
from app.core.pagination import Page
from app.core.ports import ClockDep
from app.core.tenancy import OrgAdmin, OrgReader, PlatformAdmin
from app.features.rubrics import errors, schemas, service_feedback

router = APIRouter(tags=["rubrics"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/orgs/{org_slug}/feedback-templates",
    response_model=Page[schemas.FeedbackTemplateRead],
    responses=error_responses(Forbidden),
)
async def list_feedback_templates(
    workspace: OrgReader, session: Session
) -> Page[schemas.FeedbackTemplateRead]:
    items = await service_feedback.list_feedback_templates(session, workspace.org_id)
    return Page(items=items, next_cursor=None)


@router.post(
    "/orgs/{org_slug}/feedback-templates",
    response_model=schemas.FeedbackTemplateRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        Forbidden, errors.RubricVersionNotFound, errors.RubricVersionNotPublished, errors.InvalidRubricError
    ),
)
async def create_feedback_template(
    body: schemas.CreateFeedbackTemplate, workspace: OrgAdmin, session: Session
) -> schemas.FeedbackTemplateRead:
    return await service_feedback.create_feedback_template(
        session,
        workspace.org_id,
        title=body.title,
        rubric_version_id=body.rubric_version_id,
        field_selection=body.field_selection,
    )


@router.post(
    "/orgs/{org_slug}/feedback-templates/{template_id}/versions",
    response_model=schemas.FeedbackTemplateVersionRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Forbidden, errors.FeedbackTemplateNotFound),
)
async def add_feedback_template_version(
    template_id: uuid.UUID, workspace: OrgAdmin, session: Session
) -> schemas.FeedbackTemplateVersionRead:
    return await service_feedback.add_feedback_template_version(session, workspace.org_id, template_id)


@router.patch(
    "/orgs/{org_slug}/feedback-templates/{template_id}/versions/{version}",
    response_model=schemas.FeedbackTemplateVersionRead,
    responses=error_responses(
        Forbidden, errors.FeedbackTemplateNotFound, errors.VersionNotFound, errors.NotEditableError
    ),
)
async def edit_feedback_template_version(
    template_id: uuid.UUID,
    version: int,
    body: schemas.UpdateFeedbackTemplateVersion,
    workspace: OrgAdmin,
    session: Session,
) -> schemas.FeedbackTemplateVersionRead:
    return await service_feedback.edit_feedback_template_version(
        session, workspace.org_id, template_id, version, field_selection=body.field_selection
    )


@router.post(
    "/orgs/{org_slug}/feedback-templates/{template_id}/publish",
    response_model=schemas.FeedbackTemplateVersionRead,
    responses=error_responses(
        Forbidden,
        errors.FeedbackTemplateNotFound,
        errors.VersionNotFound,
        errors.AlreadyPublishedError,
        errors.NotEditableError,
    ),
)
async def publish_feedback_template(
    template_id: uuid.UUID, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> schemas.FeedbackTemplateVersionRead:
    """Publishes the template's newest version."""
    return await service_feedback.publish_feedback_template(
        session, workspace.org_id, template_id, actor_id=workspace.principal.user_id, now=clock.now()
    )


# --- the platform's own ------------------------------------------------------


@router.get(
    "/platform/feedback-templates",
    response_model=Page[schemas.FeedbackTemplateRead],
    responses=error_responses(Forbidden),
)
async def list_platform_feedback_templates(
    admin: PlatformAdmin, session: Session
) -> Page[schemas.FeedbackTemplateRead]:
    items = await service_feedback.list_feedback_templates(session, None)
    return Page(items=items, next_cursor=None)


@router.post(
    "/platform/feedback-templates",
    response_model=schemas.FeedbackTemplateRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        Forbidden, errors.RubricVersionNotFound, errors.RubricVersionNotPublished, errors.InvalidRubricError
    ),
)
async def create_platform_feedback_template(
    body: schemas.CreateFeedbackTemplate, admin: PlatformAdmin, session: Session
) -> schemas.FeedbackTemplateRead:
    return await service_feedback.create_feedback_template(
        session,
        None,
        title=body.title,
        rubric_version_id=body.rubric_version_id,
        field_selection=body.field_selection,
    )


@router.post(
    "/platform/feedback-templates/{template_id}/versions",
    response_model=schemas.FeedbackTemplateVersionRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Forbidden, errors.FeedbackTemplateNotFound),
)
async def add_platform_feedback_version(
    template_id: uuid.UUID, admin: PlatformAdmin, session: Session
) -> schemas.FeedbackTemplateVersionRead:
    return await service_feedback.add_feedback_template_version(session, None, template_id)


@router.patch(
    "/platform/feedback-templates/{template_id}/versions/{version}",
    response_model=schemas.FeedbackTemplateVersionRead,
    responses=error_responses(
        Forbidden,
        errors.FeedbackTemplateNotFound,
        errors.VersionNotFound,
        errors.NotEditableError,
        errors.InvalidRubricError,
    ),
)
async def edit_platform_feedback_version(
    template_id: uuid.UUID,
    version: int,
    body: schemas.UpdateFeedbackTemplateVersion,
    admin: PlatformAdmin,
    session: Session,
) -> schemas.FeedbackTemplateVersionRead:
    return await service_feedback.edit_feedback_template_version(
        session, None, template_id, version, field_selection=body.field_selection
    )


@router.post(
    "/platform/feedback-templates/{template_id}/publish",
    response_model=schemas.FeedbackTemplateVersionRead,
    responses=error_responses(
        Forbidden,
        errors.FeedbackTemplateNotFound,
        errors.VersionNotFound,
        errors.AlreadyPublishedError,
    ),
)
async def publish_platform_feedback_template(
    template_id: uuid.UUID, admin: PlatformAdmin, session: Session, clock: ClockDep
) -> schemas.FeedbackTemplateVersionRead:
    return await service_feedback.publish_feedback_template(
        session, None, template_id, actor_id=admin.user_id, now=clock.now()
    )
