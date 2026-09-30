"""Mint access tokens for HTTP tests without going through login."""

from __future__ import annotations

import uuid

from app.core.auth import Membership, Principal, issue_access_token
from app.core.settings import get_settings


def mint_token(
    *,
    user_id: uuid.UUID | None = None,
    email: str = "test@example.com",
    memberships: tuple[Membership, ...] = (),
    active_org_slug: str | None = None,
    platform_admin: bool = False,
) -> str:
    principal = Principal(
        user_id=user_id or uuid.uuid4(),
        email=email,
        memberships=memberships,
        active_org_slug=active_org_slug or (memberships[0].org_slug if memberships else None),
        is_platform_admin=platform_admin,
    )
    return issue_access_token(principal, settings=get_settings())


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
