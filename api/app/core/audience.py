"""Who a piece of social content is addressed to.

Three slices — `community`, `marketplace` and `peer_practice` — each hold
things one person offers to others: a question, a practice slot, a place in a
matching queue. Until now every one of them was addressed to an entire exam,
so an institution's trainees had no way to talk among themselves and a study
group had no way to practise together.

The concept is here, in the shared kernel, rather than in any one of those
slices, because none of them owns it and all three need the same answer. It is
deliberately **opaque**: an audience is a visibility plus, at most, an
organisation and one group id. Nothing here knows what a group *is*. That is
what lets a teaching cohort, a circuit's candidates and a study group somebody
forms themselves all be the same mechanism, and it is why none of the three
slices has to reach upward into `roster` or `sittings` to use it.

Who a given viewer belongs to is answered by a lookup bound in `main.py`, the
same seam `bind_membership_lookup` and `bind_purchase_counter` already use.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Annotated, Any

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import ColumnElement, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Forbidden, InvalidInput


class Visibility(StrEnum):
    PUBLIC = "public"
    ORGANISATION = "organisation"
    GROUP = "group"


class InvalidAudience(InvalidInput):
    code = "invalid_audience"
    default_message = "That audience is not a coherent one"


class AudienceNotYours(Forbidden):
    """Posting to a room you are not in.

    A separate code from a bare 403 because the client's message is "you are
    not a member of that group", which is a different thing from "you may not
    do this at all".
    """

    code = "audience_not_yours"
    default_message = "You are not a member of that audience"


@dataclass(frozen=True)
class Audience:
    """Who may see something."""

    visibility: Visibility = Visibility.PUBLIC
    org_id: uuid.UUID | None = None
    group_id: uuid.UUID | None = None

    @property
    def is_public(self) -> bool:
        return self.visibility is Visibility.PUBLIC


@dataclass(frozen=True)
class ViewerAudiences:
    """The rooms one person is in."""

    org_ids: frozenset[uuid.UUID] = field(default_factory=frozenset)
    group_ids: frozenset[uuid.UUID] = field(default_factory=frozenset)


PUBLIC = Audience()


def build_audience(
    visibility: str | None, *, org_id: uuid.UUID | None, group_id: uuid.UUID | None
) -> Audience:
    """Read an audience off a request, refusing an incoherent one.

    Checked rather than coerced: silently treating "organisation, but no
    organisation named" as public would make a post the author believed was
    private visible to everybody.
    """
    kind = (visibility or Visibility.PUBLIC).strip().lower()
    if kind not in tuple(Visibility):
        raise InvalidAudience(f"{visibility!r} is not one of {', '.join(Visibility)}.")
    chosen = Visibility(kind)
    if chosen is Visibility.ORGANISATION and org_id is None:
        raise InvalidAudience("An organisation audience has to name the organisation.")
    if chosen is Visibility.GROUP and (group_id is None or org_id is None):
        # Both, because a group belongs to an organisation and the moderation
        # rule reads the organisation: an institution's admins may remove
        # anything addressed inside their institution, group or not.
        raise InvalidAudience("A group audience has to name the group and its organisation.")
    if chosen is Visibility.PUBLIC and (org_id or group_id):
        raise InvalidAudience("A public audience is addressed to nobody in particular.")
    return Audience(visibility=chosen, org_id=org_id, group_id=group_id)


def ensure_may_address(audience: Audience, viewer: ViewerAudiences) -> None:
    """You may only post into a room you are in.

    Both halves are checked for a group: being in the group is what makes the
    post visible, and being in the organisation is what makes it moderable.
    """
    if audience.is_public:
        return
    if audience.org_id is not None and audience.org_id not in viewer.org_ids:
        raise AudienceNotYours("You are not a member of that organisation.")
    if audience.visibility is Visibility.GROUP and audience.group_id not in viewer.group_ids:
        raise AudienceNotYours("You are not a member of that group.")


def can_see(audience: Audience, viewer: ViewerAudiences) -> bool:
    """Whether one viewer may see one thing. The SQL twin of `visible_to`."""
    if audience.visibility is Visibility.PUBLIC:
        return True
    if audience.visibility is Visibility.ORGANISATION:
        return audience.org_id in viewer.org_ids
    return audience.group_id in viewer.group_ids


def visible_to(model: Any, viewer: ViewerAudiences) -> ColumnElement[bool]:
    """The filter every audience-aware list applies.

    A query builder outside a repository, for the same reason keyset paging is:
    it is one rule, and three hand-written copies of it would be three chances
    to leave a clause out and publish an institution's conversation.
    """
    clauses: list[ColumnElement[bool]] = [model.visibility == Visibility.PUBLIC]
    if viewer.org_ids:
        clauses.append(
            (model.visibility == Visibility.ORGANISATION) & model.audience_org_id.in_(viewer.org_ids)
        )
    if viewer.group_ids:
        clauses.append((model.visibility == Visibility.GROUP) & model.audience_group_id.in_(viewer.group_ids))
    return or_(*clauses)


def addressed_to(model: Any, audience: Audience) -> ColumnElement[bool]:
    """Rows addressed to exactly this room, for narrowing a list to one of them.

    `is_not_distinct_from`, not `==`: two of the three columns are null for a
    public row, and `null = null` is null in SQL, which matches nothing.
    """
    return and_(
        model.visibility == str(audience.visibility),
        model.audience_org_id.is_not_distinct_from(audience.org_id),
        model.audience_group_id.is_not_distinct_from(audience.group_id),
    )


def audience_of(row: Any) -> Audience:
    """The audience a stored row carries."""
    return Audience(
        visibility=Visibility(row.visibility),
        org_id=row.audience_org_id,
        group_id=row.audience_group_id,
    )


class AudienceIn(BaseModel):
    """How a client says who something is for.

    Lives in core beside the rule, like `Page` and `CursorParams`: three slices
    take the same three fields, and three copies would drift.
    """

    visibility: Visibility = Visibility.PUBLIC
    org_id: uuid.UUID | None = None
    group_id: uuid.UUID | None = None

    def to_audience(self) -> Audience:
        return build_audience(self.visibility, org_id=self.org_id, group_id=self.group_id)


class AudienceOut(BaseModel):
    """Who something is for, as a reader sees it."""

    visibility: Visibility
    org_id: uuid.UUID | None = None
    group_id: uuid.UUID | None = None

    @classmethod
    def of(cls, row: Any) -> AudienceOut:
        audience = audience_of(row)
        return cls(visibility=audience.visibility, org_id=audience.org_id, group_id=audience.group_id)


class AudienceFilter:
    """Narrow a list to one room. A `Depends()`-able query parameter set."""

    def __init__(
        self,
        visibility: Annotated[Visibility | None, Query(description="Only content addressed this way")] = None,
        audience_org_id: Annotated[uuid.UUID | None, Query()] = None,
        audience_group_id: Annotated[uuid.UUID | None, Query()] = None,
    ) -> None:
        self.audience = (
            None
            if visibility is None
            else build_audience(visibility, org_id=audience_org_id, group_id=audience_group_id)
        )


ViewerLookup = Callable[[AsyncSession, uuid.UUID], Awaitable[ViewerAudiences]]

_lookup: list[ViewerLookup] = []


def bind_viewer_audiences(lookup: ViewerLookup) -> None:
    """Bound by `main.py`. Answering "which rooms is this person in?" needs
    memberships and trainee groups, which live above the slices that ask."""
    _lookup.clear()
    _lookup.append(lookup)


async def audiences_for(session: AsyncSession, user_id: uuid.UUID) -> ViewerAudiences:
    if not _lookup:
        raise RuntimeError(
            "No viewer-audience lookup bound. app.main.create_app must call bind_viewer_audiences."
        )
    return await _lookup[0](session, user_id)
