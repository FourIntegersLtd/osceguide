"""Who may read an attempt's recording, besides the person who produced it.

`service_reads._ensure_visible` is the rule every read shares: it is yours, or
you run the platform. That is right for the attempt itself, the brief and the
model answer, and wrong for the two things an examiner actually needs — the
transcript and the marking — because a supervisor watching a candidate cannot
read what their own candidate said, and b2b's console could.

So this is the one widening, and it is narrow: the caller must be the supervisor
named on the circuit that owns the attempt's slot, and must still hold a role
that may run a circuit in the organisation that owns the attempt. Being named
*is* the permission, in the same way being rostered on is the permission to join
a room (`sittings.service_join`), and an org admin who is not named on this
circuit is not let in by it.

`attempts` sits below `sittings` in the layer order, so it cannot go and look
that up. The question is asked through a seam that `composition.py` ties to this
slice's own service, which is how the other upward questions in this package are
asked — `bind_feedback_lookup` in `sittings`, `bind_interaction_complete_hook`
here.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.core.role_policy import policy
from app.features.attempts import errors
from app.features.attempts.models import Attempt

# (session, org_id, slot_id) -> the user named as the supervisor of the circuit
# that slot belongs to, or None when the slot is not this organisation's or
# nobody is named on it.
SlotSupervisorLookup = Callable[[AsyncSession, uuid.UUID, uuid.UUID], Awaitable[uuid.UUID | None]]

_supervisors: list[SlotSupervisorLookup] = []


def bind_slot_supervisor_lookup(lookup: SlotSupervisorLookup) -> None:
    _supervisors.clear()
    _supervisors.append(lookup)


async def ensure_readable(
    session: AsyncSession,
    attempt: Attempt,
    *,
    requester_id: uuid.UUID,
    is_admin: bool,
    memberships: Sequence[Membership] = (),
) -> None:
    """Owner, platform admin, or the examiner named on the attempt's circuit.

    `memberships` is what makes the third of those checkable without this slice
    learning to read another's tables. A caller who brings none — a job, or
    another slice reading on a candidate's own behalf — is served the old rule,
    which is the one it was written against and which it cannot satisfy more
    loosely than the candidate could.
    """
    if attempt.user_id == requester_id or is_admin:
        return
    if not memberships or attempt.slot_id is None or attempt.org_id is None:
        # Not a slot's attempt at all: a practice run, a peer session, a
        # debrief. There is no circuit to be named on, so there is no one.
        raise errors.AttemptNotYours()
    if not _runs_circuits_in(memberships, org_id=attempt.org_id):
        raise errors.AttemptNotYours()
    if not _supervisors:
        raise RuntimeError(
            "No slot supervisor bound. app.main.create_app must call bind_slot_supervisor_lookup."
        )
    supervisor = await _supervisors[0](session, attempt.org_id, attempt.slot_id)
    if supervisor != requester_id:
        raise errors.AttemptNotYours()


def _runs_circuits_in(memberships: Sequence[Membership], *, org_id: uuid.UUID) -> bool:
    """Whether this caller may run an examination in that organisation.

    The same predicate `OrgStaff` applies, reached through the token's own
    claims rather than a dependency: this route is not under an organisation's
    path, so there is no slug for `require_org` to have resolved.
    """
    may_run = policy("may_run_circuit")
    return any(membership.org_id == org_id and may_run(membership.role) for membership in memberships)
