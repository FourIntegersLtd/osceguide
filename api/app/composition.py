"""Tying the seams between slices that may not import each other.

A slice below another cannot import it, so the two meet at a seam: one side
declares `bind_x(...)`, and exactly one place calls it. That place used to be
`create_app`, which grew past the file cap holding both the router registry
and this; they are two different jobs and this is the one with the
explanations.

`tests/guards/test_every_seam_is_bound.py` checks both halves — that every
declared `bind_*` is called, and that a built app has each one filled in —
because the failure mode is silence: nobody calls it, and the code that needs
it raises at runtime on whichever route happens to reach it first.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.account_status import bind_account_status
from app.core.audience import bind_viewer_audiences
from app.core.auth import bind_password_gate
from app.core.memberships import bind_membership_lookup
from app.core.role_policy import bind_org_access_policy, bind_role_policy
from app.core.tenancy import bind_org_lookup
from app.features.assistant.service_seams import bind_assistant_hooks
from app.features.attempts.service_worker import bind_interaction_complete_hook
from app.features.billing.service import count_payments_for_users
from app.features.growth.service import bind_purchase_counter
from app.features.identity.service import (
    account_status,
    bind_registration_hook,
    may_call_with_temporary_password,
)
from app.features.identity.service_sessions import bind_default_workspace
from app.features.media.index import bind_vector_index
from app.features.reviews.service import slot_has_review
from app.features.roster.service import audiences_for_viewer, claim_roster_entries
from app.features.sittings.service_circuit import bind_feedback_lookup
from app.features.tenancy.service import (
    default_workspace_for,
    is_institution_admin,
    is_org_admin,
    may_read_org,
    may_run_circuit,
    memberships_for_token,
    org_permits_access,
    org_ref_by_slug,
)
from app.features.tutor_memory import jobs as tutor_jobs
from app.features.tutor_memory import service_session, service_tools
from app.features.tutor_memory.media_index import build_media_index


async def _render_assistant_session(
    session: AsyncSession, session_type: str, user_id: uuid.UUID, now: datetime
) -> dict[str, Any] | None:
    """Adapt the seam's positional shape to the slice's keyword one.

    A lambda would do it, but this is the only place the two sides meet and a
    named function is what appears in a traceback.
    """
    return await service_session.render_dashboard_session(
        session, session_type=session_type, user_id=user_id, now=now
    )


def bind_seams() -> None:
    """Called once, by `create_app`."""
    # `identity` needs a user's memberships to stamp a token but sits below
    # `tenancy`, which owns them.
    bind_membership_lookup(memberships_for_token)
    # Which workspace a fresh token lands in. `tenancy` owns the rule and sits
    # above `identity`, which builds the token.
    bind_default_workspace(default_workspace_for)
    # A temporary password reaches only the routes that replace it. The rule is
    # `identity`'s; the enforcement point is core's `get_principal`.
    bind_password_gate(may_call_with_temporary_password)
    # A deactivated account is refused on its next request, not its next
    # refresh. `identity` owns the status; the enforcement point is core's.
    bind_account_status(account_status)
    bind_org_lookup(org_ref_by_slug)
    bind_org_access_policy(org_permits_access)
    # `reviews` sits above `sittings`, so the edit lock cannot ask it directly.
    bind_feedback_lookup(slot_has_review)
    # `billing` sits above `growth`, so the partner funnel cannot count
    # purchases for itself. It reported zero until this was bound (G-2).
    bind_purchase_counter(count_payments_for_users)
    # Who can see an institution's or a group's posts. `community`,
    # `marketplace` and `peer_practice` all ask; `roster` and `tenancy`, which
    # know, both sit above them.
    bind_viewer_audiences(audiences_for_viewer)
    # The media search box and the tutor read one pgvector store. The adapter
    # belongs to `tutor_memory`, which owns `material_chunks` and sits above
    # `media`. Until this was bound the search box returned an empty list for
    # every query, always (M-3).
    bind_vector_index(build_media_index)
    # An institution rosters somebody by email before they have an account.
    # `roster` sits above `identity`, so registration announces itself here.
    bind_registration_hook(claim_roster_entries)
    # The tutor's memory sits above `assistant` and above `attempts`, so both
    # announce their moments here: what a dashboard session should be told and
    # what its tools mean, and that an interaction has finished.
    bind_assistant_hooks(
        render=_render_assistant_session,
        run_tool=service_tools.tool_hook,
        on_transcript=tutor_jobs.on_transcript,
    )
    bind_interaction_complete_hook(tutor_jobs.on_interaction_complete)
    bind_role_policy(
        may_read_org=may_read_org,
        may_run_circuit=may_run_circuit,
        is_org_admin=is_org_admin,
        is_institution_admin=is_institution_admin,
    )
