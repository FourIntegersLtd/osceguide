"""Wiring for the membership port.

`identity` needs a user's memberships to stamp a token, and sits below
`tenancy`, which owns them. This module holds the seam: a dependency that
raises until `main.py` binds the real implementation, so a missing wire fails
loudly at the first request rather than silently issuing tokens with no
memberships — which would look like a permissions bug, not a wiring bug.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership

MembershipLookup = Callable[[AsyncSession, uuid.UUID], Awaitable[list[Membership]]]

_lookup: MembershipLookup | None = None


def bind_membership_lookup(lookup: MembershipLookup) -> None:
    global _lookup
    _lookup = lookup


def get_membership_lookup() -> MembershipLookup:
    if _lookup is None:
        raise RuntimeError(
            "No membership lookup bound. app.main.create_app must call "
            "bind_membership_lookup with the tenancy implementation."
        )
    return _lookup


MembershipsFor = Annotated[MembershipLookup, Depends(get_membership_lookup)]
