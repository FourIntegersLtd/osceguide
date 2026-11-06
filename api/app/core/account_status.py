"""Wiring for the account-status port.

The token says who somebody was fifteen minutes ago. Deactivating them has to
bite on their next request, not their next refresh, and `core.auth` cannot ask
`identity` — which owns the status — because core imports no feature. So the
two meet here: `identity` binds the lookup, `get_principal` calls it. One
indexed read per authenticated request is the price, the same one a suspended
organisation already pays in `core.tenancy`.

At exam start that read is the busiest query in the product, so the answer "active" (and only
that) is kept in `core.cache` for `auth_status_cache_seconds`. A refusal is never stored, so a
deactivated person is never made more refused than the database says, and every write that
changes a status calls `forget_status` so the cached "active" goes once the change commits. With
Redis off or erroring the cache is skipped and every request reads the database, as before.
`fresh=True` skips it, for the staff paths that must not trust a copy.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import cache
from app.core.errors import ACCOUNT_DEACTIVATED_CODE, Unauthenticated
from app.core.settings import get_settings


class AccountDeactivated(Unauthenticated):
    """The token is good and the account behind it is not.

    The same code login answers with, so a client handles one refusal.
    """

    code = ACCOUNT_DEACTIVATED_CODE
    default_message = "This account is not active"


AccountStatusLookup = Callable[[AsyncSession, UUID], Awaitable[str | None]]

_lookup: list[AccountStatusLookup] = []


def bind_account_status(lookup: AccountStatusLookup) -> None:
    """Bound by `composition.bind_seams` to `identity`'s status lookup."""
    _lookup.clear()
    _lookup.append(lookup)


def status_key(user_id: UUID) -> str:
    """The cache key holding this account's "active" answer."""
    return f"acct-status:{user_id}"


def forget_status(session: AsyncSession, user_id: UUID) -> None:
    """Drop the cached answer once this transaction commits. Call it wherever a user's status is written."""
    cache.forget_after_commit(session, status_key(user_id))


async def refuse_if_deactivated(session: AsyncSession, user_id: UUID, *, fresh: bool = False) -> None:
    """Refuse a token whose account has since been deactivated.

    Unbound, nothing is checked: a harness that builds a bare app has no
    accounts to ask. `tests/guards/test_every_seam_is_bound.py` is what makes
    sure the real app binds it. An account the lookup does not know is let
    through — a token outlives a deleted row by at most its own lifetime, and
    refusing it would fail every test that mints a token for a bare id on
    something that is not a security decision.

    Only "active" is ever cached, and `fresh=True` reads the database regardless.
    """
    if not _lookup:
        return
    lookup = _lookup[0]
    ttl = get_settings().auth_status_cache_seconds

    async def confirm_active() -> None:
        """Turns away a request from an account that is no longer active."""
        found = await lookup(session, user_id)
        if found != "active":
            raise cache.ActiveOnlyRefusal(found)

    refusal = await cache.confirm_active_cached(
        status_key(user_id), ttl, fresh=fresh, confirm_active=confirm_active
    )
    if refusal is None:
        return
    status = refusal.detail
    if status is not None and status != "active":
        raise AccountDeactivated()
