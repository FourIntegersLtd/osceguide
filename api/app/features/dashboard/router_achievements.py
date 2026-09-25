"""`/me/achievements`.

Consumer-facing only: this is the practice record a person sees about themselves, not a
report about anybody else, which is why the only auth here is "signed in" rather than an
org role.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Unauthenticated, error_responses
from app.core.ports import ClockDep
from app.features.dashboard import schemas, service_achievements

router = APIRouter(tags=["dashboard"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/me/achievements",
    response_model=schemas.AchievementsRead,
    responses=error_responses(Unauthenticated),
)
async def read_achievements(
    principal: CurrentPrincipal, session: Session, clock: ClockDep
) -> schemas.AchievementsRead:
    """This person's practice record: stations touched, and the streak it adds up to.

    Nobody with zero marked attempts is refused — an empty answer is what a
    person who has never sat anything gets, not an error.
    """
    return await service_achievements.build(session, principal.user_id, now=clock.now())
