"""The SCIM 2.0 shapes (RFC 7643) an identity provider's connector sends and reads.

Attribute names are SCIM's, camelCase, set as aliases so the Python stays
snake_case; routes answer by alias. Anything a connector sends that the roster
does not keep is accepted and ignored.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _Scim(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")


# A person's name as SCIM spells it.
class ScimName(_Scim):
    given_name: str | None = Field(default=None, alias="givenName", max_length=100)
    family_name: str | None = Field(default=None, alias="familyName", max_length=100)


# One address on a SCIM user.
class ScimEmail(_Scim):
    value: str
    primary: bool | None = None
    type: str | None = None


# Where a resource lives and what kind it is.
class ScimMeta(_Scim):
    resource_type: str = Field(alias="resourceType")
    location: str | None = None
    created: datetime | None = None
    last_modified: datetime | None = Field(default=None, alias="lastModified")


# A user as a connector creates or replaces it.
class ScimUserIn(_Scim):
    schemas: list[str] = Field(default_factory=list)
    user_name: str = Field(alias="userName", min_length=3, max_length=320)
    name: ScimName | None = None
    emails: list[ScimEmail] = Field(default_factory=list)
    active: bool = True
    external_id: str | None = Field(default=None, alias="externalId")


# A trainee on the roster, as SCIM reads it.
class ScimUser(_Scim):
    schemas: list[str]
    id: uuid.UUID
    user_name: str = Field(alias="userName")
    name: ScimName
    display_name: str | None = Field(default=None, alias="displayName")
    emails: list[ScimEmail]
    active: bool
    meta: ScimMeta


# One member of a SCIM group.
class ScimMember(_Scim):
    value: str
    display: str | None = None


# A group as a connector creates or replaces it.
class ScimGroupIn(_Scim):
    schemas: list[str] = Field(default_factory=list)
    display_name: str = Field(alias="displayName", min_length=1, max_length=200)
    members: list[ScimMember] = Field(default_factory=list)
    external_id: str | None = Field(default=None, alias="externalId")


# A trainee group, as SCIM reads it.
class ScimGroup(_Scim):
    schemas: list[str]
    id: uuid.UUID
    display_name: str = Field(alias="displayName")
    members: list[ScimMember]
    meta: ScimMeta


# A PATCH request: a list of operations, each `op`, `path` and `value`.
class ScimPatch(_Scim):
    schemas: list[str] = Field(default_factory=list)
    operations: list[dict[str, Any]] = Field(alias="Operations", min_length=1, max_length=1000)


# A page of users, SCIM's ListResponse.
class ScimUserList(_Scim):
    schemas: list[str]
    total_results: int = Field(alias="totalResults")
    start_index: int = Field(alias="startIndex")
    items_per_page: int = Field(alias="itemsPerPage")
    resources: list[ScimUser] = Field(alias="Resources")


# A page of groups, SCIM's ListResponse.
class ScimGroupList(_Scim):
    schemas: list[str]
    total_results: int = Field(alias="totalResults")
    start_index: int = Field(alias="startIndex")
    items_per_page: int = Field(alias="itemsPerPage")
    resources: list[ScimGroup] = Field(alias="Resources")


# What this server supports, for a connector that asks before it starts.
class ScimServiceProviderConfig(_Scim):
    schemas: list[str]
    patch: dict[str, bool]
    bulk: dict[str, Any]
    filter: dict[str, Any]
    change_password: dict[str, bool] = Field(alias="changePassword")
    sort: dict[str, bool]
    etag: dict[str, bool]
    authentication_schemes: list[dict[str, Any]] = Field(alias="authenticationSchemes")


# A new SCIM token. `token` is shown this once and never again.
class ScimTokenIssued(BaseModel):
    id: uuid.UUID
    label: str
    token: str
    token_prefix: str
    created_at: datetime


# A SCIM token as the admin screen lists it: never the token itself.
class ScimTokenRead(BaseModel):
    id: uuid.UUID
    label: str
    token_prefix: str
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None


class IssueScimToken(BaseModel):
    """Name the connector this token is for, so it can be told apart and revoked."""

    label: str = Field(min_length=1, max_length=100)
