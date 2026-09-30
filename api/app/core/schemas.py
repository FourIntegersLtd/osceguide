"""Response shapes shared by more than one slice.

A slice's own `schemas.py` may not import another slice's (`test_schemas_are_not_rows`
enforces this), and two slices returning identically named response models makes
FastAPI qualify both in `openapi.json`, renaming a type platform-web already
imports. A shape genuinely shared by more than one route lives here instead,
where every slice's `schemas.py` may import it.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class RecordFieldRead(BaseModel):
    """One column of a `records` block: the key in each record, and its heading."""

    key: str
    label: str


class AudienceBlockRead(BaseModel):
    """One block of a section, as one audience may read it."""

    id: str
    label: str
    type: str
    role: str
    value: Any
    # A `records` block's template-declared `{key, label}` columns, in order;
    # None for every other type, and for records that left them to the data.
    fields: list[RecordFieldRead] | None = None


class AudienceSectionRead(BaseModel):
    """A station's content, grouped by its template's sections, for one audience.

    The one read model every screen that shows a candidate, a patient actor or
    an examiner a station's material is built from. Shared here rather than
    owned by `stations`: `attempts` and `peer_practice` both build one, and a
    slice's `schemas.py` may not import another slice's.
    """

    id: str
    title: str
    audience: str
    blocks: list[AudienceBlockRead]


class InvitationRead(BaseModel):
    """A re-sent invitation. The token itself is never returned; it goes only to
    the address it was minted for.

    Shared by roster's and tenancy's resend routes.
    """

    email: str
    invited_to: str
