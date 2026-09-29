"""Response shapes shared by more than one slice.

A slice's own `schemas.py` may not import another slice's (`test_schemas_are_not_rows`
enforces this), and two slices returning identically named response models makes
FastAPI qualify both in `openapi.json`, renaming a type platform-web already
imports. A shape genuinely shared by more than one route lives here instead,
where every slice's `schemas.py` may import it.
"""

from __future__ import annotations

from pydantic import BaseModel


class InvitationRead(BaseModel):
    """A re-sent invitation. The token itself is never returned; it goes only to
    the address it was minted for.

    Shared by roster's and tenancy's resend routes.
    """

    email: str
    invited_to: str
