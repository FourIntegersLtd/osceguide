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
