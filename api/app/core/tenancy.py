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
from app.core.role_policy import RolePredicate, org_permits_access, policy


class OrgNotFound(NotFound):
    """No such organisation.

    Defined here rather than in the tenancy slice because `require_org` raises
    it and core may not import a feature. The slice re-exports this exact
    class: two classes sharing one error code would be free to drift, and the
    code is the contract the frontend switches on.
    """

    code = "org_not_found"
    default_message = "No such organisation"


class OrgSuspended(Forbidden):
    """The organisation is suspended, so its members may not act in it.

    Its own code, not a bare 403: the client should say "your institution's
    access has been suspended", which is a different conversation from "you do
    not have permission".
    """

    code = "organization_suspended"
    default_message = "This organisation's access has been suspended"


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


async def resolve_workspace(
    session: AsyncSession,
    principal: Principal,
    org_slug: str,
    *,
    predicate: RolePredicate,
    allow_platform_admin: bool = True,
) -> Workspace:
    """The whole access rule, as a plain function.

    Separated from the dependency because a `text/event-stream` route cannot
    take the request session — it would hold that transaction open for the life
    of the connection — and so cannot take `require_org` either. The rule has
    one implementation and both entry points call it; a second copy for streams
    is exactly how `b2b` ended up with a check that was almost the same.
    """
    membership = principal.membership_for(org_slug)
    if membership is None:
        if not (allow_platform_admin and principal.is_platform_admin):
            # 403 rather than 404: the caller did authenticate, and a 404
            # here would let membership be probed by response code.
            raise Forbidden()
        org = await _lookup()(session, org_slug)
        if org is None:
            raise OrgNotFound()
        return Workspace(org_id=org.id, org_slug=org.slug, role=None, principal=principal)

    if not predicate(membership.role):
        raise Forbidden()

    # The status is read here rather than carried in the token. A token
    # lives 15 minutes, and a suspension that takes a quarter of an hour to
    # bite is not a suspension. One indexed read per org-scoped request is
    # the price of it taking effect now.
    org = await _lookup()(session, org_slug)
    if org is None:
        raise OrgNotFound()
    if not org_permits_access(org.status) and not principal.is_platform_admin:
        raise OrgSuspended()

    return Workspace(org_id=membership.org_id, org_slug=org_slug, role=membership.role, principal=principal)


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
        return await resolve_workspace(
            session,
            principal,
            org_slug,
            predicate=predicate,
            allow_platform_admin=allow_platform_admin,
        )

    return dependency


def admin_org_ids(principal: Principal) -> frozenset[uuid.UUID]:
    """Organisations this caller administers, read from the token's own claims.

    No database round trip: the memberships are already in the token. Used
    where a rule is "an institution may moderate what is addressed inside it"
    rather than "this route belongs to one organisation".
    """
    is_admin = policy("is_org_admin")
    return frozenset(m.org_id for m in principal.memberships if is_admin(m.role))


async def require_platform_admin(principal: CurrentPrincipal) -> Principal:
    if not principal.is_platform_admin:
        raise Forbidden()
    return principal


PlatformAdmin = Annotated[Principal, Depends(require_platform_admin)]


# Declared after the factory so slices can depend on access without importing
# one another: `workspace: OrgAdmin` is the whole of it.
def may_read_org_policy() -> RolePredicate:
    """The predicate behind `OrgReader`, for a caller that cannot use a dependency.

    A stream resolves its own workspace (see `resolve_workspace`) and needs the
    same rule the annotation applies, not a second spelling of it.
    """
    return policy("may_read_org")


def may_run_circuit_policy() -> RolePredicate:
    """The predicate behind `OrgStaff`, for a stream that resolves its own workspace."""
    return policy("may_run_circuit")


OrgReader = Annotated[Workspace, Depends(require_org(policy("may_read_org")))]
# Running an examination: an org admin or its assigned supervisor. Not
# `OrgReader`, which admits the trainee sitting the circuit.
OrgStaff = Annotated[Workspace, Depends(require_org(policy("may_run_circuit")))]
OrgAdmin = Annotated[Workspace, Depends(require_org(policy("is_org_admin"), allow_platform_admin=False))]
OrgInstitutionAdmin = Annotated[
    Workspace, Depends(require_org(policy("is_institution_admin"), allow_platform_admin=False))
]
