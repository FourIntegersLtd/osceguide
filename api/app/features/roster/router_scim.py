"""SCIM 2.0 routes (RFC 7644) an identity provider provisions an organisation's roster through (E-21).

Under `/orgs/{org_slug}/scim/v2/`, authenticated by the organisation's SCIM
bearer token rather than a person's session. Bodies and errors are SCIM's own,
as `application/scim+json`. The token routes beside them are the org admin's.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import Forbidden, error_responses
from app.core.ports import ClockDep
from app.core.tenancy import OrgAdmin
from app.features.roster import errors, schemas_scim, service_scim

SCIM_MEDIA_TYPE = "application/scim+json"


class ScimResponse(JSONResponse):
    """JSON under SCIM's media type."""

    media_type = SCIM_MEDIA_TYPE


router = APIRouter(tags=["scim"])
scim = APIRouter(prefix="/orgs/{org_slug}/scim/v2", tags=["scim"], default_response_class=ScimResponse)

Session = Annotated[AsyncSession, Depends(get_session)]
ScimOrg = Annotated[uuid.UUID, Depends(service_scim.require_scim_org)]
Filter = Annotated[str | None, Query(alias="filter", max_length=500)]
StartIndex = Annotated[int | None, Query(alias="startIndex", ge=1)]
Count = Annotated[int | None, Query(alias="count", ge=0)]

_READ = error_responses(errors.ScimUnauthorized, errors.ScimResourceNotFound)
_LIST = error_responses(errors.ScimUnauthorized, errors.ScimInvalidFilter)


def _base(request: Request, org_slug: str) -> str:
    """This organisation's SCIM root, for the `meta.location` of what a route returns."""
    return str(request.url_for("scim_service_provider_config", org_slug=org_slug)).removesuffix(
        "/ServiceProviderConfig"
    )


# --- tokens: the organisation's admin ---------------------------------------------


# Issue a SCIM bearer token for this organisation's identity provider. Shown once.
@router.post(
    "/orgs/{org_slug}/scim/tokens",
    response_model=schemas_scim.ScimTokenIssued,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Forbidden),
)
async def issue_scim_token(
    body: schemas_scim.IssueScimToken, workspace: OrgAdmin, session: Session
) -> schemas_scim.ScimTokenIssued:
    return await service_scim.issue_token(
        session, workspace.org_id, label=body.label, actor_id=workspace.principal.user_id
    )


# This organisation's SCIM tokens, newest first, without the tokens themselves.
@router.get(
    "/orgs/{org_slug}/scim/tokens",
    response_model=list[schemas_scim.ScimTokenRead],
    responses=error_responses(Forbidden),
)
async def list_scim_tokens(workspace: OrgAdmin, session: Session) -> list[schemas_scim.ScimTokenRead]:
    return await service_scim.list_tokens(session, workspace.org_id)


# Revoke a SCIM token; the connector using it is refused from the next request.
@router.delete(
    "/orgs/{org_slug}/scim/tokens/{token_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(Forbidden, errors.ScimTokenNotFound),
)
async def revoke_scim_token(
    token_id: uuid.UUID, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> Response:
    await service_scim.revoke_token(session, workspace.org_id, token_id, now=clock.now())
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- discovery -------------------------------------------------------------------


# What this SCIM server supports.
@scim.get(
    "/ServiceProviderConfig",
    name="scim_service_provider_config",
    response_model=schemas_scim.ScimServiceProviderConfig,
    response_model_by_alias=True,
    responses=error_responses(errors.ScimUnauthorized),
)
async def scim_service_provider_config(org_id: ScimOrg) -> schemas_scim.ScimServiceProviderConfig:
    _ = org_id
    return service_scim.service_provider_config()


# --- Users -----------------------------------------------------------------------


# A page of the roster as SCIM users; `filter=userName eq "..."` finds one person.
@scim.get("/Users", response_model=schemas_scim.ScimUserList, responses=_LIST)
async def scim_list_users(
    org_slug: str,
    request: Request,
    org_id: ScimOrg,
    session: Session,
    filter_expression: Filter = None,
    start_index: StartIndex = None,
    count: Count = None,
) -> schemas_scim.ScimUserList:
    return await service_scim.list_users(
        session,
        org_id,
        filter_expression=filter_expression,
        start_index=start_index,
        count=count,
        base_url=_base(request, org_slug),
    )


# One trainee as a SCIM user.
@scim.get("/Users/{user_id}", response_model=schemas_scim.ScimUser, responses=_READ)
async def scim_read_user(
    org_slug: str, user_id: uuid.UUID, request: Request, org_id: ScimOrg, session: Session
) -> schemas_scim.ScimUser:
    return await service_scim.read_user(session, org_id, user_id, base_url=_base(request, org_slug))


# Roster and invite a person.
@scim.post(
    "/Users",
    response_model=schemas_scim.ScimUser,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(errors.ScimUnauthorized, errors.ScimUniqueness, errors.ScimError),
)
async def scim_create_user(
    org_slug: str,
    body: schemas_scim.ScimUserIn,
    request: Request,
    org_id: ScimOrg,
    session: Session,
    clock: ClockDep,
) -> schemas_scim.ScimUser:
    return await service_scim.create_user(
        session, org_id, body, now=clock.now(), base_url=_base(request, org_slug)
    )


# Replace a user's name and active state.
@scim.put(
    "/Users/{user_id}",
    response_model=schemas_scim.ScimUser,
    responses=error_responses(errors.ScimUnauthorized, errors.ScimResourceNotFound, errors.ScimMutability),
)
async def scim_replace_user(
    org_slug: str,
    user_id: uuid.UUID,
    body: schemas_scim.ScimUserIn,
    request: Request,
    org_id: ScimOrg,
    session: Session,
    clock: ClockDep,
) -> schemas_scim.ScimUser:
    return await service_scim.replace_user(
        session, org_id, user_id, body, now=clock.now(), base_url=_base(request, org_slug)
    )


# Change a user's active state or name, one operation at a time.
@scim.patch(
    "/Users/{user_id}",
    response_model=schemas_scim.ScimUser,
    responses=error_responses(
        errors.ScimUnauthorized, errors.ScimResourceNotFound, errors.ScimMutability, errors.ScimError
    ),
)
async def scim_patch_user(
    org_slug: str,
    user_id: uuid.UUID,
    body: schemas_scim.ScimPatch,
    request: Request,
    org_id: ScimOrg,
    session: Session,
    clock: ClockDep,
) -> schemas_scim.ScimUser:
    return await service_scim.patch_user(
        session, org_id, user_id, body.operations, now=clock.now(), base_url=_base(request, org_slug)
    )


# Deactivate a user: access is revoked, and what was decided about them is kept.
@scim.delete(
    "/Users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=_READ,
)
async def scim_delete_user(
    user_id: uuid.UUID, org_id: ScimOrg, session: Session, clock: ClockDep
) -> Response:
    await service_scim.deactivate_user(session, org_id, user_id, now=clock.now())
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Groups ----------------------------------------------------------------------


# This organisation's trainee groups as SCIM groups; `filter=displayName eq "..."` finds one.
@scim.get("/Groups", response_model=schemas_scim.ScimGroupList, responses=_LIST)
async def scim_list_groups(
    org_slug: str,
    request: Request,
    org_id: ScimOrg,
    session: Session,
    filter_expression: Filter = None,
    start_index: StartIndex = None,
    count: Count = None,
) -> schemas_scim.ScimGroupList:
    return await service_scim.list_groups(
        session,
        org_id,
        filter_expression=filter_expression,
        start_index=start_index,
        count=count,
        base_url=_base(request, org_slug),
    )


# One trainee group as a SCIM group, with its members.
@scim.get("/Groups/{group_id}", response_model=schemas_scim.ScimGroup, responses=_READ)
async def scim_read_group(
    org_slug: str, group_id: uuid.UUID, request: Request, org_id: ScimOrg, session: Session
) -> schemas_scim.ScimGroup:
    return await service_scim.read_group(session, org_id, group_id, base_url=_base(request, org_slug))


# Create a group with its members.
@scim.post(
    "/Groups",
    response_model=schemas_scim.ScimGroup,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(errors.ScimUnauthorized, errors.ScimUniqueness, errors.ScimError),
)
async def scim_create_group(
    org_slug: str, body: schemas_scim.ScimGroupIn, request: Request, org_id: ScimOrg, session: Session
) -> schemas_scim.ScimGroup:
    return await service_scim.create_group(session, org_id, body, base_url=_base(request, org_slug))


# Replace a group's name and its whole membership.
@scim.put(
    "/Groups/{group_id}",
    response_model=schemas_scim.ScimGroup,
    responses=error_responses(
        errors.ScimUnauthorized, errors.ScimResourceNotFound, errors.ScimUniqueness, errors.ScimError
    ),
)
async def scim_replace_group(
    org_slug: str,
    group_id: uuid.UUID,
    body: schemas_scim.ScimGroupIn,
    request: Request,
    org_id: ScimOrg,
    session: Session,
) -> schemas_scim.ScimGroup:
    return await service_scim.replace_group(
        session, org_id, group_id, body, base_url=_base(request, org_slug)
    )


# Rename a group, or add, remove or replace its members.
@scim.patch(
    "/Groups/{group_id}",
    response_model=schemas_scim.ScimGroup,
    responses=error_responses(
        errors.ScimUnauthorized, errors.ScimResourceNotFound, errors.ScimUniqueness, errors.ScimError
    ),
)
async def scim_patch_group(
    org_slug: str,
    group_id: uuid.UUID,
    body: schemas_scim.ScimPatch,
    request: Request,
    org_id: ScimOrg,
    session: Session,
) -> schemas_scim.ScimGroup:
    return await service_scim.patch_group(
        session, org_id, group_id, body.operations, base_url=_base(request, org_slug)
    )


# Remove a group the identity provider has deleted, members and all.
@scim.delete(
    "/Groups/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=_READ,
)
async def scim_delete_group(group_id: uuid.UUID, org_id: ScimOrg, session: Session) -> Response:
    await service_scim.delete_group(session, org_id, group_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


router.include_router(scim)
