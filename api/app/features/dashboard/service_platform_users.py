"""The account directory, assembled once per page rather than once per row.

An account is one row whatever it holds, and the columns are other slices' facts:
`billing` says who paid, `attempts` how much they have done, `entitlements` what is live,
`identity` whether they are signed in now. The page is fetched from `identity`, then
enriched with four bulk reads; filters that turn on another slice's fact are handed to
`identity` as sets of ids.
"""

from __future__ import annotations

import uuid
from collections.abc import Collection
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import service_platform as attempts
from app.features.billing import service_platform as billing
from app.features.catalog import service as catalog
from app.features.dashboard import errors
from app.features.dashboard.schemas import DirectorySummary, DirectoryUser, ExamDirectorySummary
from app.features.entitlements import service_platform as entitlements
from app.features.identity import service_platform as accounts
from app.features.identity.service_platform import SupportUser

ACCESS_FACETS = ("paid", "trial", "not_started")


async def _facets(
    session: AsyncSession, *, access: str | None, plan_code: str | None
) -> tuple[set[uuid.UUID] | None, set[uuid.UUID] | None]:
    """`(only_ids, except_ids)` for the facets other slices own.

    `paid` is anyone with a payment; `trial` anyone unpaid who has started
    something; `not_started` anyone unpaid who has not. A plan narrows to the
    people whose latest payment bought it.
    """
    only: set[uuid.UUID] | None = None
    except_: set[uuid.UUID] | None = None
    if access == "paid":
        only = await billing.payer_ids(session)
    elif access == "trial":
        only = await attempts.attempted_user_ids(session)
        except_ = await billing.payer_ids(session)
    elif access == "not_started":
        except_ = await billing.payer_ids(session) | await attempts.attempted_user_ids(session)
    if plan_code:
        on_plan = await billing.payer_ids_on_plan(session, plan_code)
        only = on_plan if only is None else only & on_plan
    return only, except_


async def list_directory(
    session: AsyncSession,
    *,
    query: str | None,
    exam_code: str | None,
    status: str | None,
    access: str | None,
    plan_code: str | None,
    unassigned: bool,
    limit: int,
    cursor: dict[str, Any] | None,
    now: datetime,
) -> tuple[list[DirectoryUser], str | None]:
    """`unassigned` is the group under no exam heading: accounts that chose
    none and hold no live grant. It wins over `exam_code`, which would
    contradict it."""
    only, except_ = await _facets(session, access=access, plan_code=plan_code)
    if unassigned:
        exam_code = None
        except_ = (except_ or set()) | await _covered(session, now=now)
    exam_ids = await entitlements.live_user_ids_for_exam(session, exam_code, now=now) if exam_code else None
    rows, next_cursor = await accounts.search_users(
        session,
        query=query,
        limit=limit,
        cursor=cursor,
        status=status,
        exam_code=exam_code,
        exam_user_ids=exam_ids,
        only_ids=only,
        except_ids=except_,
        no_exam=unassigned,
    )
    return await _enrich(session, rows, now=now), next_cursor


async def _covered(session: AsyncSession, *, now: datetime) -> set[uuid.UUID]:
    """Everyone holding a live grant for any published exam."""
    covered: set[uuid.UUID] = set()
    for exam in await catalog.exam_refs(session):
        covered |= await entitlements.live_user_ids_for_exam(session, exam.code, now=now)
    return covered


async def read_directory_user_by_id(
    session: AsyncSession, user_id: uuid.UUID, *, now: datetime
) -> DirectoryUser:
    """The directory's row for one account, for the detail screen's header."""
    user = await accounts.user_by_id(session, user_id)
    if user is None:
        raise errors.UserNotFound()
    [row] = await _enrich(session, [user], now=now)
    return row


async def _enrich(session: AsyncSession, rows: list[SupportUser], *, now: datetime) -> list[DirectoryUser]:
    ids = [row.id for row in rows]
    payments = await billing.latest_payment_by_user(session, ids)
    counts = await attempts.attempt_counts(session, ids)
    grants = await entitlements.live_grants_by_user(session, ids, now=now)
    signed_in = await accounts.signed_in_user_ids(session, ids, now=now)
    out = []
    for row in rows:
        live = grants.get(row.id, [])
        ends = [grant.ends_at for grant in live]
        payment = payments.get(row.id)
        out.append(
            DirectoryUser(
                id=row.id,
                email=row.email,
                name=row.name,
                created_at=row.created_at,
                status=row.status,
                is_platform_admin=row.is_platform_admin,
                exam_code=row.exam_code,
                last_login_at=row.last_login_at,
                signed_in=row.id in signed_in,
                has_paid=payment is not None,
                plan_code=payment.plan_code if payment else None,
                last_paid_at=payment.paid_at if payment else None,
                access_ends_at=None if not ends or any(end is None for end in ends) else max(ends),  # type: ignore[type-var]
                live_exam_codes=sorted({grant.exam_code for grant in live if grant.exam_code}),
                attempt_count=counts.get(row.id, 0),
            )
        )
    return out


async def summarise_directory(session: AsyncSession, *, now: datetime) -> DirectorySummary:
    """Per published exam: how many accounts, and the paid / trial / not
    started split. An account is on an exam by its own choice or by a live
    grant, so one person may be counted under two exams; `unassigned` is
    those under none.
    """
    paid = await billing.payer_ids(session)
    started = await attempts.attempted_user_ids(session)
    trial = started - paid
    exams = []
    covered: set[uuid.UUID] = set()
    for exam in await catalog.exam_refs(session):
        live = await entitlements.live_user_ids_for_exam(session, exam.code, now=now)
        covered |= live
        exams.append(
            ExamDirectorySummary(
                code=exam.code,
                name=exam.name,
                users=await _count(session, exam.code, live),
                paid=await _count(session, exam.code, live, only_ids=paid),
                trial=await _count(session, exam.code, live, only_ids=trial),
                not_started=await _count(session, exam.code, live, except_ids=paid | started),
            )
        )
    total = await accounts.count_users_matching(session)
    on_some_exam = (
        await accounts.count_users_matching(session, exam_code=None, only_ids=covered) if covered else 0
    )
    naming_one = 0
    for summary in exams:
        naming_one += await accounts.count_users_matching(session, exam_code=summary.code, except_ids=covered)
    return DirectorySummary(exams=exams, unassigned=total - on_some_exam - naming_one, total=total)


async def _count(
    session: AsyncSession,
    exam_code: str,
    live: Collection[uuid.UUID],
    *,
    only_ids: set[uuid.UUID] | None = None,
    except_ids: set[uuid.UUID] | None = None,
) -> int:
    return await accounts.count_users_matching(
        session, exam_code=exam_code, exam_user_ids=live, only_ids=only_ids, except_ids=except_ids
    )
