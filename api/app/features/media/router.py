"""The routes a candidate browses the media library through, and a platform admin authors
study material with: slide decks, summaries, blog posts and podcasts.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal, MaybePrincipal
from app.core.db import get_session
from app.core.errors import Forbidden, Unauthenticated, error_responses
from app.core.pagination import CursorParams
from app.core.ports import ClockDep, VectorIndex
from app.core.tenancy import PlatformAdmin
from app.features.media import errors, schemas, service, service_search

router = APIRouter(tags=["media"])

Session = Annotated[AsyncSession, Depends(get_session)]
Index = Annotated[VectorIndex, Depends(service_search.get_vector_index)]


@router.get(
    "/media",
    response_model=schemas.MediaPage,
    responses=error_responses(errors.UnknownExamError, errors.UnknownMediaKindError),
)
async def list_published(
    session: Session,
    principal: MaybePrincipal,
    clock: ClockDep,
    page: Annotated[CursorParams, Depends()],
    kind: Annotated[str | None, Query()] = None,
    status: Annotated[
        str | None,
        Query(description="Authoring filter: draft, published, or all (platform admin only)."),
    ] = None,
    exam_code: Annotated[
        str | None,
        Query(description="Only this exam's material, plus material tagged with no exam."),
    ] = None,
    q: Annotated[str | None, Query(description="A fragment of a title or a summary.", max_length=300)] = None,
) -> schemas.MediaPage:
    """Published material: the titles to anybody, the bodies to subscribers.

    No token required, because a signed-out visitor still needs the landing
    page's article rail and a shared link still needs to say what it points
    at. What a token changes is `content`: the slide decks and the A to Z are
    the paid half of the product.

    `exam_code` and `q` narrow the query server-side.
    """
    is_admin = bool(principal and principal.is_platform_admin)
    unlocked = await service_search.unlocked_exam_ids(
        session, principal.user_id if principal else None, now=clock.now()
    )
    media_items, next_cursor, total_count = await service.list_catalog(
        session,
        kind=kind,
        limit=page.limit,
        cursor=page.cursor,
        status=status,
        viewer_is_admin=is_admin,
        exam_code=exam_code,
        search=q,
        unlocked=unlocked,
    )
    return schemas.MediaPage(items=media_items, next_cursor=next_cursor, total_count=total_count)


@router.get(
    "/media/by-id/{item_id}",
    response_model=schemas.MediaRead,
    responses=error_responses(Unauthenticated, Forbidden, errors.ItemNotFound),
)
async def read_by_id(item_id: uuid.UUID, admin: PlatformAdmin, session: Session) -> schemas.MediaRead:
    """Staff authoring: read any row by primary key, including drafts."""
    return await service.read_by_id(session, item_id, viewer_is_admin=True)


@router.get(
    "/media-search",
    response_model=schemas.MediaSearchPage,
    responses=error_responses(Unauthenticated, errors.EmptyQueryError, errors.UnknownMediaKindError),
)
async def search(
    principal: CurrentPrincipal,
    session: Session,
    index: Index,
    clock: ClockDep,
    page: Annotated[CursorParams, Depends()],
    q: Annotated[str, Query(description="What to search for")],
    kind: Annotated[
        str | None, Query(description="Only this kind of material: slide_deck, summary, blog, podcast.")
    ] = None,
) -> schemas.MediaSearchPage:
    """Over the material this reader holds, not the whole library.

    Paged like every other list here: `total_count` is how many hits the query
    matched, `next_cursor` continues past the ones this page carried.
    """
    hits, next_cursor, total_count = await service_search.search_page(
        session,
        query=q,
        index=index,
        kind=kind,
        limit=page.limit,
        cursor=page.cursor,
        unlocked=await service_search.unlocked_exam_ids(session, principal.user_id, now=clock.now()),
    )
    return schemas.MediaSearchPage(items=hits, next_cursor=next_cursor, total_count=total_count)


@router.get(
    "/media/lookup",
    response_model=schemas.MediaRead,
    responses=error_responses(errors.ItemNotFound),
)
async def read_by_slug_lookup(
    principal: MaybePrincipal,
    session: Session,
    clock: ClockDep,
    slug: Annotated[str, Query(min_length=1, description="The item's canonical slug")],
) -> schemas.MediaRead:
    """Same as `GET /media/{slug}`; query form avoids path-encoding edge cases in clients."""
    return await service.read_by_slug(
        session,
        slug,
        viewer_is_admin=bool(principal and principal.is_platform_admin),
        unlocked=await service_search.unlocked_exam_ids(
            session, principal.user_id if principal else None, now=clock.now()
        ),
    )


@router.get(
    "/media/{slug}",
    response_model=schemas.MediaRead,
    responses=error_responses(errors.ItemNotFound),
)
async def read_by_slug(
    slug: str, principal: MaybePrincipal, session: Session, clock: ClockDep
) -> schemas.MediaRead:
    """A draft is 404 to everyone but an admin: its existence is not public.

    Readable without a token, for the same reason the listing is — but a token
    decides two things: whether a draft exists at all, and whether the body
    comes with it. `locked` says which, so the client can offer the upgrade
    rather than render an empty article.
    """
    return await service.read_by_slug(
        session,
        slug,
        viewer_is_admin=bool(principal and principal.is_platform_admin),
        unlocked=await service_search.unlocked_exam_ids(
            session, principal.user_id if principal else None, now=clock.now()
        ),
    )


# Creates a new draft. Only a platform admin can author study material.
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


# Replaces a draft's editable fields. Refuses once the item is published.
@router.patch(
    "/media/{item_id}",
    response_model=schemas.MediaRead,
    responses=error_responses(Forbidden, errors.ItemNotFound, errors.NotEditableError),
)
async def update(
    item_id: uuid.UUID, body: schemas.UpdateMedia, admin: PlatformAdmin, session: Session
) -> schemas.MediaRead:
    return await service.update(
        session,
        item_id,
        title=body.title,
        summary=body.summary,
        content=body.content,
    )


# Deletes a draft outright. Refuses once the item is published: publishing is a one-way door.
@router.delete(
    "/media/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(Forbidden, errors.ItemNotFound, errors.NotDeletableError),
)
async def delete_draft(item_id: uuid.UUID, admin: PlatformAdmin, session: Session) -> None:
    await service.delete_draft(session, item_id)


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
