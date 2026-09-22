from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class SsoBinding(BaseModel):
    kind: str
    value: str


class SsoConfigRead(BaseModel):
    """The whole arrangement, for whoever administers it."""

    org_id: uuid.UUID
    org_slug: str
    provider: str
    issuer: str | None
    enabled: bool
    sso_only: bool
    sign_in_label: str
    default_exam_code: str | None
    bindings: list[SsoBinding] = Field(default_factory=list)


class SaveSsoConfig(BaseModel):
    provider: str
    issuer: str | None = Field(default=None, max_length=255)
    enabled: bool = False
    sso_only: bool = False
    sign_in_label: str | None = Field(default=None, max_length=80)
    default_exam_code: str | None = Field(default=None, max_length=32)
    hosts: list[str] = Field(default_factory=list)
    email_domains: list[str] = Field(default_factory=list)


class SsoSignIn(BaseModel):
    """What a sign-in page may know before anybody has proved anything.

    Deliberately thin. This is served without a token, to anyone who asks, so
    it carries what a button needs and nothing about the organisation beyond
    the name it already puts on its own front page. No issuer, no bindings, no
    counts: those are configuration, and configuration is for administrators.
    """

    org_slug: str
    org_name: str
    provider: str
    sign_in_label: str
    # Whether to draw the password form at all.
    sso_only: bool
    default_exam_code: str | None = None


class SsoLoginRequest(BaseModel):
    """Which organisation to start signing in to.

    The slug comes from `GET /auth/sso/sign-in`, which a sign-in page already
    called to learn whether this visitor's organisation signs in elsewhere.
    """

    org_slug: str = Field(min_length=1, max_length=100)


class SsoLoginResult(BaseModel):
    """Where to send the browser to sign in.

    A URL rather than a server-side redirect: the frontend owns navigation and
    the platform issues no cookies (ADR 0004). The broker sends the browser
    back to `{frontend_url}/auth/sso/callback`, which posts the token it was
    handed to `POST /auth/sso/callback`.
    """

    sign_in_url: str


class SsoCallbackRequest(BaseModel):
    """The token the broker handed back, and the organisation it was for."""

    org_slug: str = Field(min_length=1, max_length=100)
    token: str = Field(min_length=1, max_length=4096)


class SsoSession(BaseModel):
    """A platform session — what a login returns, minus the profile.

    The frontend stores these and reads the person from `GET /me`, so the user
    object is not duplicated into this slice's contract; `identity` owns its
    shape and the broker's job ends at the tokens.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 - a scheme name, not a secret
    expires_in: int
