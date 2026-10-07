"""Who may read an attempt's recording, besides the person who produced it.

`service_reads._ensure_visible` covers the attempt itself, the brief and the model answer: yours, or
you run the platform. The transcript and the marking need one narrow widening beyond that: the caller
must be the supervisor named on the circuit that owns the attempt's slot, and must still hold a role
that may run a circuit in that organisation. Being named *is* the permission for a supervisor — the
same way being rostered on is the permission to join a room (`sittings.service_join`). An institution
administrator of that organisation reads any of its slots without being named, since they review and
sign off the results; an admin of another organisation is not let in.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.core.role_policy import policy
from app.features.attempts import errors
from app.features.attempts.models import Attempt
from app.features.results.errors import NotReleased
from app.features.sittings import service_reads as sittings


async def ensure_readable(
    session: AsyncSession,
    attempt: Attempt,
    *,
    requester_id: uuid.UUID,
    is_admin: bool,
    memberships: Sequence[Membership] = (),
) -> None:
    """Raise `AttemptNotYours` unless the module's access rule admits this caller.

    `memberships` is what makes the supervisor and administrator checks possible
    without this slice reading another's tables. A caller who brings none (a job,
    or another slice reading on a candidate's own behalf) gets owner-or-admin only.
    """
    if is_admin:
        return
    if attempt.user_id == requester_id:
        await _ensure_released_to_candidate(session, attempt)
        return
    if not memberships or attempt.slot_id is None or attempt.org_id is None:
        # Not a slot's attempt at all: a practice run, a peer session, a
        # debrief. There is no circuit to be named on, so there is no one.
        raise errors.AttemptNotYours()
    if not _runs_circuits_in(memberships, org_id=attempt.org_id):
        raise errors.AttemptNotYours()
    if _administers(memberships, org_id=attempt.org_id):
        return
    supervisor = await sittings.supervisor_for_slot(session, attempt.org_id, attempt.slot_id)
    if supervisor != requester_id:
        raise errors.AttemptNotYours()


async def _ensure_released_to_candidate(session: AsyncSession, attempt: Attempt) -> None:
    """An exam slot's transcript and marks feed a decision, so its candidate reads them only once
    that decision is released (`result_not_released` before). A training slot, and any attempt
    that is not a slot's, is the candidate's own at once (R-1).
    """
    if attempt.slot_id is None or attempt.org_id is None:
        return
    found = await sittings.slot_and_sitting(session, attempt.org_id, attempt.slot_id)
    if found is not None and found[1].mode != "exam":
        return
    # `results` reaches `attempts` through `reviews`, so its import waits until call time.
    from app.features.results import service_candidate as results

    if found is None:
        raise errors.AttemptNotYours()
    if await results.sealed_sittings(session, [found[1].id], attempt.user_id):
        raise NotReleased()


def _runs_circuits_in(memberships: Sequence[Membership], *, org_id: uuid.UUID) -> bool:
    """Whether this caller may run an examination in that organisation.

    The same predicate `OrgStaff` applies, reached through the token's own
    claims rather than a dependency: this route is not under an organisation's
    path, so there is no slug for `require_org` to have resolved.
    """
    may_run = policy("may_run_circuit")
    return any(membership.org_id == org_id and may_run(membership.role) for membership in memberships)


def _administers(memberships: Sequence[Membership], *, org_id: uuid.UUID) -> bool:
    """Whether this caller is an institution administrator of that organisation."""
    is_admin = policy("is_institution_admin")
    return any(membership.org_id == org_id and is_admin(membership.role) for membership in memberships)
