from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Forbidden, Unauthenticated, error_responses
from app.core.pagination import CursorParams, Page
from app.core.ports import ClockDep, VectorIndex
from app.core.tenancy import PlatformAdmin
from app.features.media import errors, schemas, service

router = APIRouter(tags=["media"])

Session = Annotated[AsyncSession, Depends(get_session)]
Index = Annotated[VectorIndex, Depends(service.get_vector_index)]


@router.get(
    "/media",
    response_model=Page[schemas.MediaRead],
    responses=error_responses(errors.UnknownExamError, Unauthenticated, errors.UnknownMediaKindError),
)
async def list_published(
    principal: CurrentPrincipal,
    session: Session,
    page: Annotated[CursorParams, Depends()],
    kind: Annotated[str | None, Query()] = None,
) -> Page[schemas.MediaRead]:
    items, next_cursor = await service.list_published(
        session, kind=kind, limit=page.limit, cursor=page.cursor
    )
    return Page(items=items, next_cursor=next_cursor)


@router.get(
    "/media/{slug}",
    response_model=schemas.MediaRead,
    responses=error_responses(Unauthenticated, errors.ItemNotFound),
)
async def read_by_slug(slug: str, principal: CurrentPrincipal, session: Session) -> schemas.MediaRead:
    """A draft is 404 to everyone but an admin: its existence is not public."""
    return await service.read_by_slug(session, slug, viewer_is_admin=principal.is_platform_admin)


@router.get(
    "/media-search",
    response_model=Page[schemas.SearchHit],
    responses=error_responses(Unauthenticated, errors.EmptyQueryError),
)
async def search(
    principal: CurrentPrincipal,
    session: Session,
    index: Index,
    q: Annotated[str, Query(description="What to search for")],
) -> Page[schemas.SearchHit]:
    items = await service.search(session, query=q, index=index)
    return Page(items=items, next_cursor=None)


@router.post(
    "/media",
    response_model=schemas.MediaRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        errors.UnknownExamError,
        Forbidden,
        errors.UnknownMediaKindError,
        errors.SlugTaken,
        errors.UnusableTitleError,
    ),
)
async def create(body: schemas.CreateMedia, admin: PlatformAdmin, session: Session) -> schemas.MediaRead:
    return await service.create(
        session,
        kind=body.kind,
        title=body.title,
        summary=body.summary,
        content=body.content,
        exam_code=body.exam_code,
        author_id=admin.user_id,
    )


@router.patch(
    "/media/{item_id}",
    response_model=schemas.MediaRead,
    responses=error_responses(Forbidden, errors.ItemNotFound, errors.NotEditableError),
)
async def update(
    item_id: uuid.UUID, body: schemas.UpdateMedia, admin: PlatformAdmin, session: Session
) -> schemas.MediaRead:
    return await service.update(
        session, item_id, title=body.title, summary=body.summary, content=body.content
    )


@router.post(
    "/media/{item_id}/publish",
    response_model=schemas.MediaRead,
    responses=error_responses(Forbidden, errors.ItemNotFound, errors.AlreadyPublishedError),
)
async def publish(
    item_id: uuid.UUID,
    admin: PlatformAdmin,
    session: Session,
    index: Index,
    clock: ClockDep,
) -> schemas.MediaRead:
    """Indexed on publish, so a draft nobody can read does not surface in search."""
    return await service.publish(session, item_id, index=index, now=clock.now())
