"""Correcting a sitting that has already been scheduled.

One route, and the reason it is its own module: everything else in this slice
either composes a sitting (`service.py`) or runs one (`service_run.py`), and both
are acts that happen in order. This is the one that happens *afterwards* — the
name was typed wrong, the date moved, the programme was the other one — and what
it may touch is decided by whether anybody has already been examined against the
answer.

Ported from b2b's `PUT /orgs/{org}/sessions/{id}`, which was also a partial
document sent by a screen that carried three fields, and which also refused to
move the type or the feedback template once a circuit was live while letting the
name through. The feedback template is not a field on a sitting here: it is
resolved from the programme, so `programme_id` is the field that carries it.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import raise_mapped
from app.features.sittings import domain, domain_edit, repository, repository_reads, service, service_binding
from app.features.sittings.models import Sitting
from app.features.sittings.schemas import SittingRead, UpdateSitting
from app.features.sittings.service import _REFUSALS, _require_sitting

# The fields this route may write. Anything else on a sitting belongs to
# something with a better claim on it: `status` to the run machine,
# `rubric_version_id` to the programme it is resolved from.
EDITABLE = frozenset({"name", "mode", "sitting_type", "scheduled_for", "programme_id"})


async def update_sitting(
    session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID, *, body: UpdateSitting
) -> SittingRead:
    """Change what the caller sent, and only that.

    An absent field is left alone, so the edit screen does not have to restate a
    sitting to rename it — the same partial semantics the legacy route had, where
    the body was dumped with `exclude_unset` before it was written.
    """
    sent = EDITABLE & set(body.model_fields_set)
    if not sent:
        # Nothing was asked for. Answered with the sitting rather than refused,
        # because a PUT of the document as read has to be a no-op; an empty patch
        # is a client whose form was not dirty, not a malformed request.
        return await service.read_sitting(session, org_id, sitting_id)

    sitting = await _require_sitting(session, org_id, sitting_id)
    changing = {field for field in sent if _requested(body, sitting, field)}

    try:
        if "mode" in changing:
            # Asked before the freeze below, and refused for a sitting with any
            # circuits at all: the mode is what a circuit's slots are composed
            # from, and this route composes nothing.
            circuits = await repository_reads.count_sitting_circuits(session, org_id, sitting_id)
            domain_edit.ensure_mode_changeable(circuit_count=circuits)
        begun = await repository_reads.sitting_has_begun(session, org_id, sitting_id)
        domain_edit.ensure_sitting_editable(domain_edit.SittingEditState(begun=begun), changing=changing)
    except (domain.InvalidCircuit, domain_edit.SittingLocked) as exc:
        raise_mapped(exc, _REFUSALS)

    values: dict[str, Any] = {field: getattr(body, field) for field in changing if field != "programme_id"}
    if "programme_id" in changing and body.programme_id is not None:
        # The rubric a sitting is marked against is resolved from its programme,
        # so changing the programme is how the marking basis is changed — and the
        # binding moves with it, in the same write, rather than being left
        # pointing at the exam the sitting no longer offers.
        values["programme_id"] = body.programme_id
        values["rubric_version_id"] = await service_binding.rubric_version_for_programme(
            session, org_id, body.programme_id
        )

    if values:
        await repository.update_sitting(session, org_id, sitting_id, **values)
    return await service.read_sitting(session, org_id, sitting_id)


def _requested(body: UpdateSitting, sitting: Sitting, field: str) -> bool:
    """Whether this field was sent *and* says something the sitting does not.

    The second half is what keeps the freeze honest. A screen that PUTs the
    whole document back — which is what a PUT invites — has not asked to change
    the mode, it has restated it, and refusing that because somebody has started
    an examination would be a route refusing to save a form nobody edited.

    A null is a request to clear for `scheduled_for` alone, because "not
    scheduled" is a state a sitting can genuinely be in. On the other four it is
    the schema's default rather than an intention, so it is read as absent.
    """
    wanted: object = getattr(body, field)
    if wanted is None and field != "scheduled_for":
        return False
    current: object = getattr(sitting, field)
    if isinstance(wanted, datetime) and isinstance(current, datetime):
        return _instant(wanted) != _instant(current)
    return wanted != current


def _instant(value: datetime) -> datetime:
    """The same moment, whichever clock it was written against.

    A body that says `2027-01-12T09:00` with no offset arrives naive and means
    the reader's local time; the column is `timestamptz` and comes back aware.
    Comparing the two directly raises a TypeError, so a naive date is read as
    UTC — which is what the legacy screen's `datetime-local` input produced on
    the wire, and what the create route already stores.
    """
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
