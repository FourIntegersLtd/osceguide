"""Org access as dependencies, so no handler decides it for itself.

A route declares the access it needs and receives a `Workspace` — the org id it
may touch, already checked. `b2b` spread these checks through handlers and had
a `find_slot_by_id_global` that skipped them entirely; making the check the way
you *obtain* the org id means forgetting it leaves you with nothing to query.

The predicates live in `features/tenancy/domain.py`. This module only wires
them to HTTP.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal, Principal
from app.core.db import get_session
from app.core.errors import Forbidden, NotFound


class OrgMissing(NotFound):
    """A platform admin asked for an organisation that does not exist."""

    code = "org_not_found"
    default_message = "No such organisation"


@dataclass(frozen=True)
class OrgRef:
    """The little a guard needs to know about an organisation."""

    id: uuid.UUID
    slug: str
    status: str


OrgLookup = Callable[[AsyncSession, str], Awaitable[OrgRef | None]]

_org_lookup: OrgLookup | None = None


def bind_org_lookup(lookup: OrgLookup) -> None:
    """Bound by `main.py` to the tenancy implementation.

    Core cannot import a slice, and resolving a slug is a tenancy concern, so
    the two meet at a seam the composition root ties together.
    """
    global _org_lookup
    _org_lookup = lookup


def _lookup() -> OrgLookup:
    if _org_lookup is None:
        raise RuntimeError("No org lookup bound. app.main.create_app must call bind_org_lookup.")
    return _org_lookup


@dataclass(frozen=True)
class Workspace:
    """An organisation the caller has been cleared to act in."""

    org_id: uuid.UUID
    org_slug: str
    role: str | None
    principal: Principal

    @property
    def is_platform_admin(self) -> bool:
        return self.principal.is_platform_admin


OrgSlug = Annotated[str, Path(description="Organisation slug")]

RolePredicate = Callable[[str | None], bool]


def require_org(
    predicate: RolePredicate, *, allow_platform_admin: bool = True
) -> Callable[..., Awaitable[Workspace]]:
    """Build a dependency that resolves an org slug and checks the caller's role.

    `allow_platform_admin` is deliberately explicit rather than implicit: a
    platform admin may read any organisation for support, but does not thereby
    become its administrator — the legacy policy is emphatic that a console
    admin inherits no org powers, and that is worth preserving.
    """

    async def dependency(
        org_slug: OrgSlug,
        principal: CurrentPrincipal,
        session: Annotated[AsyncSession, Depends(get_session)],
    ) -> Workspace:
        membership = principal.membership_for(org_slug)
        if membership is None:
            if not (allow_platform_admin and principal.is_platform_admin):
                # 403 rather than 404: the caller did authenticate, and a 404
                # here would let membership be probed by response code.
                raise Forbidden()
            org = await _lookup()(session, org_slug)
            if org is None:
                raise OrgMissing()
            return Workspace(org_id=org.id, org_slug=org.slug, role=None, principal=principal)

        if not predicate(membership.role):
            raise Forbidden()
        return Workspace(
            org_id=membership.org_id, org_slug=org_slug, role=membership.role, principal=principal
        )

    return dependency


# The role predicates belong to the tenancy slice; the dependency factory is
# core's. They meet here, bound once by `main.py`, so every other slice can
# write `workspace: OrgAdmin` without importing another slice's service.
_policies: dict[str, RolePredicate] = {}


def bind_role_policy(**predicates: RolePredicate) -> None:
    _policies.update(predicates)


def _policy(name: str) -> RolePredicate:
    def predicate(role: str | None) -> bool:
        try:
            return _policies[name](role)
        except KeyError as exc:
            raise RuntimeError(
                f"No {name!r} role policy bound. app.main.create_app must call bind_role_policy."
            ) from exc

    return predicate


async def require_platform_admin(principal: CurrentPrincipal) -> Principal:
    if not principal.is_platform_admin:
        raise Forbidden()
    return principal


PlatformAdmin = Annotated[Principal, Depends(require_platform_admin)]


# Declared after the factory so slices can depend on access without importing
# one another: `workspace: OrgAdmin` is the whole of it.
OrgReader = Annotated[Workspace, Depends(require_org(_policy("may_read_org")))]
OrgAdmin = Annotated[Workspace, Depends(require_org(_policy("is_org_admin"), allow_platform_admin=False))]
OrgInstitutionAdmin = Annotated[
    Workspace, Depends(require_org(_policy("is_institution_admin"), allow_platform_admin=False))
]
