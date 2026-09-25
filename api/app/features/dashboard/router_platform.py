"""The platform console's account directory. Every route is `PlatformAdmin`.

`GET /platform/users` (tenancy) finds an account by email; this is the directory the
support screen lists — grouped by exam, with the paid / trial / plan / status facets.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import Forbidden, error_responses
from app.core.pagination import CursorParams, Page
from app.core.ports import ClockDep
from app.core.tenancy import PlatformAdmin
from app.features.dashboard import errors, schemas, service_platform_users

router = APIRouter(tags=["dashboard"])

Session = Annotated[AsyncSession, Depends(get_session)]

ACCESS_PATTERN = "^(paid|trial|not_started)$"
STATUS_PATTERN = "^(active|deactivated)$"


@router.get(
    "/platform/directory",
    response_model=Page[schemas.DirectoryUser],
    responses=error_responses(Forbidden),
)
async def list_directory(
    admin: PlatformAdmin,
    session: Session,
    clock: ClockDep,
    page: Annotated[CursorParams, Depends()],
    q: Annotated[str | None, Query(description="Part of an email address or a name")] = None,
    exam_code: Annotated[
        str | None, Query(max_length=32, description="Chosen at sign-up, or held live")
    ] = None,
    status: Annotated[str | None, Query(pattern=STATUS_PATTERN)] = None,
    access: Annotated[
        str | None,
        Query(
            pattern=ACCESS_PATTERN,
            description="paid: any payment; trial: unpaid and started; not_started: neither",
        ),
    ] = None,
    plan_code: Annotated[
        str | None, Query(max_length=32, description="Whose latest payment bought this plan")
    ] = None,
    unassigned: Annotated[
        bool,
        Query(description="Only accounts naming no exam and holding no live access; overrides exam_code"),
    ] = False,
) -> Page[schemas.DirectoryUser]:
    """Every account, newest first, with the facts beside each: payment, activity,
    entitlements and sign-in status."""
    _ = admin
    items, next_cursor = await service_platform_users.list_directory(
        session,
        query=q,
        exam_code=exam_code,
        status=status,
        access=access,
        plan_code=plan_code,
        unassigned=unassigned,
        limit=page.limit,
        cursor=page.cursor,
        now=clock.now(),
    )
    return Page(items=items, next_cursor=next_cursor)


@router.get(
    "/platform/directory/summary",
    response_model=schemas.DirectorySummary,
    responses=error_responses(Forbidden),
)
async def summarise_directory(
    admin: PlatformAdmin, session: Session, clock: ClockDep
) -> schemas.DirectorySummary:
    """How many accounts each exam has, and how many of them paid, are on
    trial or have not started — the headings of the grouped list."""
    _ = admin
    return await service_platform_users.summarise_directory(session, now=clock.now())


@router.get(
    "/platform/directory/users/{user_id}",
    response_model=schemas.DirectoryUser,
    responses=error_responses(Forbidden, errors.UserNotFound),
)
async def read_directory_user(
    user_id: uuid.UUID, admin: PlatformAdmin, session: Session, clock: ClockDep
) -> schemas.DirectoryUser:
    """The directory's row for one account, for the top of the detail screen."""
    _ = admin
    return await service_platform_users.read_directory_user_by_id(session, user_id, now=clock.now())
