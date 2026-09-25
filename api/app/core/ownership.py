"""Who owns a row: the platform, or one organisation.

Content the platform authors and content an institution authors live in the
same tables, distinguished by `owner_kind` with `org_id NULL` for the platform
half. Two different questions, and confusing them is how a tenancy bug gets
written:

- **Who may change this?** Exactly one owner. Use :func:`owned_by`.
- **Who may see this?** The owner, plus everyone, because the platform library
  is offered to every organisation. Use :func:`visible_to`.

Both are needed because SQL `NULL = NULL` is null, not true: a plain
`Model.org_id == org_id` silently matches no platform row at all, which reads
as "the library is empty" rather than as an error.
"""

from __future__ import annotations

import uuid
from typing import Any, cast

from sqlalchemy import ColumnElement, or_

__all__ = ["OWNER_KINDS", "owned_by", "owner_kind_for", "visible_to"]

OWNER_KINDS = ("platform", "org")


def owner_kind_for(org_id: uuid.UUID | None) -> str:
    """The `owner_kind` that goes with an org id, or its absence."""
    return "org" if org_id is not None else "platform"


def owned_by(model: Any, org_id: uuid.UUID | None) -> ColumnElement[bool]:
    """Rows this owner owns, and no others. The predicate for writes.

    `org_id=None` means the platform's own rows, so a platform admin editing
    the library cannot reach an institution's stations, and an org admin
    cannot edit the library.
    """
    if org_id is None:
        return cast("ColumnElement[bool]", model.org_id.is_(None))
    return cast("ColumnElement[bool]", model.org_id == org_id)


def visible_to(model: Any, org_id: uuid.UUID | None) -> ColumnElement[bool]:
    """Rows this owner may read: its own, plus the platform library.

    A platform caller (`org_id=None`) sees only platform rows — the library is
    shared downward, never an organisation's content upward.
    """
    if org_id is None:
        return cast("ColumnElement[bool]", model.org_id.is_(None))
    return or_(model.org_id.is_(None), model.org_id == org_id)
