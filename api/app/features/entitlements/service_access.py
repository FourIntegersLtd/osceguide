"""Which exams a person may open, resolved against the catalogue.

`service.py` answers "may this one attempt start" — the gate every attempt goes through. This
answers the broader question the screens ask before that: which exams to show at all. The rule
itself is `domain_access.exam_access`.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog import service as catalog
from app.features.entitlements import service
from app.features.entitlements.domain_access import ExamAccess, exam_access
from app.features.entitlements.errors import NotEntitled
from app.features.identity import service as identity


async def exam_access_for(session: AsyncSession, user_id: uuid.UUID, *, now: datetime) -> ExamAccess:
    """The exams this person may open, most-entitled first.

    Live grants only: `list_for_user` answers with every row somebody has ever held, revoked
    and lapsed included, and reading exam codes off it without checking `live` would give a
    lapsed subscriber a paying one's catalogue.
    """
    grants = await service.list_for_user(session, user_id, now=now)
    user = await identity.user_ref_by_id(session, user_id)
    return exam_access(
        live_entitlement_codes=[grant.exam_code for grant in grants if grant.live],
        account_exam_code=user.exam_code if user else None,
        published_codes=await catalog.exam_codes(session),
    )


async def require_exam_access(
    session: AsyncSession, user_id: uuid.UUID, *, exam_code: str, now: datetime
) -> None:
    """Refuse a browse of an exam this person has no business in.

    Weaker than `service.require`, and deliberately: this admits the exam an account was opened
    for as well as the ones it holds, because a trial user has to be able to see the library
    before they can sit anything in it. Anything carrying paid content asks `service.require`
    instead.
    """
    access = await exam_access_for(session, user_id, now=now)
    if exam_code not in access.codes:
        raise NotEntitled(details={"reason": "no_entitlement"})
