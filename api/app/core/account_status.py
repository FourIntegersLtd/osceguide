"""Wiring for the account-status port.

The token says who somebody was fifteen minutes ago. Deactivating them has to
bite on their next request, not their next refresh, and `core.auth` cannot ask
`identity` — which owns the status — because core imports no feature. So the
two meet here: `identity` binds the lookup, `get_principal` calls it. One
indexed read per authenticated request is the price, the same one a suspended
organisation already pays in `core.tenancy`.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ACCOUNT_DEACTIVATED_CODE, Unauthenticated


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


async def refuse_if_deactivated(session: AsyncSession, user_id: UUID) -> None:
    """Refuse a token whose account has since been deactivated.

    Unbound, nothing is checked: a harness that builds a bare app has no
    accounts to ask. `tests/guards/test_every_seam_is_bound.py` is what makes
    sure the real app binds it. An account the lookup does not know is let
    through — a token outlives a deleted row by at most its own lifetime, and
    refusing it would fail every test that mints a token for a bare id on
    something that is not a security decision.
    """
    if not _lookup:
        return
    status = await _lookup[0](session, user_id)
    if status is not None and status != "active":
        raise AccountDeactivated()
