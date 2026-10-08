"""SCIM 2.0 provisioning of an organisation's roster by its identity provider (E-21).

Users are trainees and Groups are trainee groups. Every change goes through the
roster's own use cases — `service.add_trainees`, `service.set_access`,
`service_edit.update_trainee` and `service_groups` — so a person provisioned
by Entra is invited, linked and revoked exactly as one added on the roster
screen is. This module only translates between SCIM and those.

A connector authenticates with a per-organisation bearer token issued by the
organisation's admin, stored as a hash. Deleting a user deactivates them, as
revoking access does: their results must outlive their roster standing.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import Depends, Header
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.core.db import get_session
from app.core.ports import ClockDep
from app.features.roster import (
    domain_scim,
    errors,
    repository,
    repository_scim,
    service,
    service_edit,
    service_groups,
)
from app.features.roster.models import ScimToken, Trainee
from app.features.roster.schemas import CreateTrainee, UpdateTrainee
from app.features.roster.schemas_scim import (
    ScimEmail,
    ScimGroup,
    ScimGroupIn,
    ScimGroupList,
    ScimMember,
    ScimMeta,
    ScimName,
    ScimServiceProviderConfig,
    ScimTokenIssued,
    ScimTokenRead,
    ScimUser,
    ScimUserIn,
    ScimUserList,
)
from app.features.sittings import service_absence
from app.features.tenancy import service as tenancy
from app.features.tenancy import service_audit as tenancy_audit
from app.features.tenancy.service_audit import SCIM_CONNECTOR

TOKEN_BYTES = 32
TOKEN_PREFIX = "scim_"  # noqa: S105 - a label on every token, not a secret
PREFIX_SHOWN = 12


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# --- tokens, managed by the organisation's admin -----------------------------------


async def issue_token(
    session: AsyncSession, org_id: uuid.UUID, *, label: str, actor: Principal
) -> ScimTokenIssued:
    """Mint a token for this organisation's connector. The plaintext is returned this once."""
    token = TOKEN_PREFIX + secrets.token_urlsafe(TOKEN_BYTES)
    stored = await repository_scim.create_token(
        session,
        org_id,
        token_hash=_hash(token),
        token_prefix=token[:PREFIX_SHOWN],
        label=label.strip(),
        created_by=actor.user_id,
    )
    await tenancy_audit.record_for_owner(
        session,
        org_id=org_id,
        actor=actor,
        action="scim.token_issued",
        target_type="scim_token",
        target_id=str(stored.id),
        summary=f"Provisioning token issued for {stored.label}",
    )
    return ScimTokenIssued(
        id=stored.id,
        label=stored.label,
        token=token,
        token_prefix=stored.token_prefix,
        created_at=stored.created_at,
    )


async def list_tokens(session: AsyncSession, org_id: uuid.UUID) -> list[ScimTokenRead]:
    """Every token this organisation has issued, newest first, never the token itself."""
    return [_token_read(token) for token in await repository_scim.tokens_for(session, org_id)]


async def revoke_token(
    session: AsyncSession, org_id: uuid.UUID, token_id: uuid.UUID, *, actor: Principal, now: datetime
) -> None:
    """Stop a token working at once. Revoking twice keeps the first time."""
    if not await repository_scim.revoke_token(session, org_id, token_id, at=now):
        raise errors.ScimTokenNotFound()
    await tenancy_audit.record_for_owner(
        session,
        org_id=org_id,
        actor=actor,
        action="scim.token_revoked",
        target_type="scim_token",
        target_id=str(token_id),
        summary="Provisioning token revoked",
    )


# --- authenticating the connector ------------------------------------------------


async def require_scim_org(
    org_slug: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    clock: ClockDep,
    authorization: Annotated[str | None, Header()] = None,
) -> uuid.UUID:
    """The organisation a SCIM request is for, proven by its bearer token.

    One refusal for every failure — no header, a token from another
    organisation, a revoked one, a suspended organisation — so a probe learns
    nothing about which it was.
    """
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise errors.ScimUnauthorized()
    org = await tenancy.org_ref_by_slug(session, org_slug)
    if org is None or not tenancy.org_permits_access(org.status):
        raise errors.ScimUnauthorized()
    stored = await repository_scim.live_token_by_hash(session, org.id, _hash(token.strip()))
    if stored is None:
        raise errors.ScimUnauthorized()
    await repository_scim.mark_used(session, org.id, stored.id, at=clock.now())
    return org.id


def service_provider_config() -> ScimServiceProviderConfig:
    """What this server supports (RFC 7643 §5), for a connector that asks first."""
    return ScimServiceProviderConfig(
        schemas=["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
        patch={"supported": True},
        bulk={"supported": False, "maxOperations": 0, "maxPayloadSize": 0},
        filter={"supported": True, "maxResults": domain_scim.MAX_PAGE},
        change_password={"supported": False},
        sort={"supported": False},
        etag={"supported": False},
        authentication_schemes=[
            {
                "type": "oauthbearertoken",
                "name": "Bearer token",
                "description": "A token issued by the organisation's admin under SCIM settings.",
            }
        ],
    )


# --- Users -----------------------------------------------------------------------


async def list_users(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    filter_expression: str | None,
    start_index: int | None,
    count: int | None,
    base_url: str,
) -> ScimUserList:
    """A page of the roster, or the one person a `userName eq` filter names."""
    try:
        matched = domain_scim.parse_filter(filter_expression, allowed=domain_scim.USER_FILTERS)
    except domain_scim.InvalidFilter as exc:
        raise errors.ScimInvalidFilter() from exc
    offset, limit = domain_scim.page_window(start_index, count)
    if matched is not None and matched[0] == "id":
        trainee = await _trainee_or_none(session, org_id, matched[1])
        trainees, total = ([trainee], 1) if trainee is not None else ([], 0)
        trainees = trainees[offset : offset + limit]
    else:
        email = matched[1] if matched is not None else None
        trainees, total = await repository_scim.trainees_page(
            session, org_id, email=email, offset=offset, limit=limit
        )
    return ScimUserList(
        schemas=[domain_scim.LIST_SCHEMA],
        total_results=total,
        start_index=offset + 1,
        items_per_page=len(trainees),
        resources=[_user(trainee, base_url) for trainee in trainees],
    )


async def read_user(
    session: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, *, base_url: str
) -> ScimUser:
    """One trainee as a SCIM user, as it now stands in the database."""
    trainee = await repository_scim.trainee_fresh(session, org_id, user_id)
    if trainee is None:
        raise errors.ScimResourceNotFound()
    return _user(trainee, base_url)


async def create_user(
    session: AsyncSession, org_id: uuid.UUID, body: ScimUserIn, *, now: datetime, base_url: str
) -> ScimUser:
    """Roster and invite a person, through the same use case the roster screen's upload uses.

    A person already on the roster is a 409 `uniqueness`, which is how a
    connector learns to link rather than create.
    """
    entry = _create_trainee(body)
    outcome = await service.add_trainees(session, org_id, entries=[entry], actor=SCIM_CONNECTOR, now=now)
    if not outcome.created:
        raise errors.ScimUniqueness()
    created = outcome.created[0]
    if not body.active:
        await service.set_access(session, org_id, created.id, revoked=True, actor=SCIM_CONNECTOR, now=now)
    return await read_user(session, org_id, created.id, base_url=base_url)


async def replace_user(
    session: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    body: ScimUserIn,
    *,
    now: datetime,
    base_url: str,
) -> ScimUser:
    """PUT: the name and active state as sent. The address cannot change."""
    trainee = await _require_trainee(session, org_id, user_id)
    if _address(body).lower() != trainee.email.lower():
        raise errors.ScimMutability()
    name = body.name or ScimName()
    await service_edit.update_trainee(
        session,
        org_id,
        user_id,
        body=UpdateTrainee(first_name=name.given_name, last_name=name.family_name),
        fields_sent={"first_name", "last_name"},
    )
    await _set_active(session, org_id, trainee, active=body.active, now=now)
    return await read_user(session, org_id, user_id, base_url=base_url)


async def patch_user(
    session: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    operations: list[dict[str, Any]],
    *,
    now: datetime,
    base_url: str,
) -> ScimUser:
    """PATCH: `active`, and the given and family names. Other attributes are ignored."""
    trainee = await _require_trainee(session, org_id, user_id)
    try:
        changes = domain_scim.user_patch(operations)
    except domain_scim.InvalidPatch as exc:
        raise errors.ScimError(str(exc)) from exc
    if changes.user_name is not None and changes.user_name.lower() != trainee.email.lower():
        raise errors.ScimMutability()
    fields_sent: set[str] = set()
    if changes.first_name is not None or changes.clear_first_name:
        fields_sent.add("first_name")
    if changes.last_name is not None or changes.clear_last_name:
        fields_sent.add("last_name")
    if fields_sent:
        await service_edit.update_trainee(
            session,
            org_id,
            user_id,
            body=UpdateTrainee(first_name=changes.first_name, last_name=changes.last_name),
            fields_sent=fields_sent,
        )
    if changes.active is not None:
        await _set_active(session, org_id, trainee, active=changes.active, now=now)
    return await read_user(session, org_id, user_id, base_url=base_url)


async def deactivate_user(
    session: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, *, now: datetime
) -> None:
    """DELETE: revoke access rather than delete, so what was decided about them survives."""
    trainee = await _require_trainee(session, org_id, user_id)
    await _set_active(session, org_id, trainee, active=False, now=now)


# --- Groups ----------------------------------------------------------------------


async def list_groups(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    filter_expression: str | None,
    start_index: int | None,
    count: int | None,
    base_url: str,
) -> ScimGroupList:
    """This organisation's groups, or the one a `displayName eq` filter names, with members."""
    try:
        matched = domain_scim.parse_filter(filter_expression, allowed=domain_scim.GROUP_FILTERS)
    except domain_scim.InvalidFilter as exc:
        raise errors.ScimInvalidFilter() from exc
    groups = await service_groups.list_groups(session, org_id)
    if matched is not None:
        attribute, wanted = matched
        groups = [
            group
            for group in groups
            if (str(group.id) == wanted if attribute == "id" else group.label.lower() == wanted.lower())
        ]
    offset, limit = domain_scim.page_window(start_index, count)
    page = groups[offset : offset + limit]
    resources = [await _group(session, org_id, group.id, group.label, base_url) for group in page]
    return ScimGroupList(
        schemas=[domain_scim.LIST_SCHEMA],
        total_results=len(groups),
        start_index=offset + 1,
        items_per_page=len(resources),
        resources=resources,
    )


async def read_group(
    session: AsyncSession, org_id: uuid.UUID, group_id: uuid.UUID, *, base_url: str
) -> ScimGroup:
    """One trainee group as a SCIM group."""
    group = await _require_group(session, org_id, group_id)
    return await _group(session, org_id, group.id, group.label, base_url)


async def create_group(
    session: AsyncSession, org_id: uuid.UUID, body: ScimGroupIn, *, base_url: str
) -> ScimGroup:
    """A new group, with its members set in the same request."""
    try:
        group = await service_groups.add_group(session, org_id, label=body.display_name)
    except errors.GroupExists as exc:
        raise errors.ScimUniqueness() from exc
    await _set_members(session, org_id, group.id, [member.value for member in body.members])
    return await read_group(session, org_id, group.id, base_url=base_url)


async def replace_group(
    session: AsyncSession, org_id: uuid.UUID, group_id: uuid.UUID, body: ScimGroupIn, *, base_url: str
) -> ScimGroup:
    """PUT: the name and the whole membership, as sent."""
    await _rename_group(session, org_id, group_id, body.display_name)
    await _set_members(session, org_id, group_id, [member.value for member in body.members])
    return await read_group(session, org_id, group_id, base_url=base_url)


async def patch_group(
    session: AsyncSession,
    org_id: uuid.UUID,
    group_id: uuid.UUID,
    operations: list[dict[str, Any]],
    *,
    base_url: str,
) -> ScimGroup:
    """PATCH: rename, and add, remove or replace members."""
    try:
        changes = domain_scim.group_patch(operations)
    except domain_scim.InvalidPatch as exc:
        raise errors.ScimError(str(exc)) from exc
    current = [str(member_id) for member_id in await _member_ids(session, org_id, group_id)]
    if changes.display_name is not None:
        await _rename_group(session, org_id, group_id, changes.display_name)
    members = domain_scim.apply_members(current, changes)
    if members != current:
        await _set_members(session, org_id, group_id, members)
    return await read_group(session, org_id, group_id, base_url=base_url)


async def delete_group(session: AsyncSession, org_id: uuid.UUID, group_id: uuid.UUID) -> None:
    """DELETE: the identity provider has removed the group, so it is emptied and removed.

    The roster screen refuses to delete a group with members so nobody empties
    one by accident; a connector's delete is the provider saying so on purpose.
    """
    await _require_group(session, org_id, group_id)
    await service_groups.set_group_members(session, org_id, group_id, trainee_ids=[])
    await service_groups.delete_group(session, org_id, group_id)


# --- mapping ---------------------------------------------------------------------


def _create_trainee(body: ScimUserIn) -> CreateTrainee:
    """The roster's own create request, from a SCIM user."""
    name = body.name or ScimName()
    try:
        return CreateTrainee(email=_address(body), first_name=name.given_name, last_name=name.family_name)
    except ValidationError as exc:
        raise errors.ScimError("userName must be an email address") from exc


def _address(body: ScimUserIn) -> str:
    """The address to roster: `userName` when it is one, else the primary email."""
    if "@" in body.user_name:
        return body.user_name.strip()
    primary = next((email for email in body.emails if email.primary), body.emails[0] if body.emails else None)
    return primary.value.strip() if primary is not None else body.user_name.strip()


async def _set_active(
    session: AsyncSession, org_id: uuid.UUID, trainee: Trainee, *, active: bool, now: datetime
) -> None:
    """Revoke or restore access, only when it changes, so a repeat keeps the first date."""
    if (trainee.access_revoked_at is None) != active:
        await service.set_access(
            session, org_id, trainee.id, revoked=not active, actor=SCIM_CONNECTOR, now=now
        )
        if not active and trainee.user_id is not None:
            await service_absence.skip_unstarted_stations(session, org_id, trainee.user_id, now=now)


async def _require_trainee(session: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID) -> Trainee:
    """The trainee, or SCIM's 404."""
    trainee = await repository.trainee_by_id(session, org_id, user_id)
    if trainee is None:
        raise errors.ScimResourceNotFound()
    return trainee


async def _trainee_or_none(session: AsyncSession, org_id: uuid.UUID, raw_id: str) -> Trainee | None:
    """The trainee a filter's id names, or None for an id that is not even a uuid."""
    try:
        return await repository.trainee_by_id(session, org_id, uuid.UUID(raw_id))
    except ValueError:
        return None


async def _require_group(session: AsyncSession, org_id: uuid.UUID, group_id: uuid.UUID) -> Any:
    """The group, or SCIM's 404."""
    group = next(
        (group for group in await service_groups.list_groups(session, org_id) if group.id == group_id), None
    )
    if group is None:
        raise errors.ScimResourceNotFound()
    return group


async def _member_ids(session: AsyncSession, org_id: uuid.UUID, group_id: uuid.UUID) -> list[uuid.UUID]:
    """Who is in the group now, or SCIM's 404."""
    try:
        return await service_groups.group_member_ids(session, org_id, group_id)
    except errors.GroupNotFound as exc:
        raise errors.ScimResourceNotFound() from exc


async def _rename_group(session: AsyncSession, org_id: uuid.UUID, group_id: uuid.UUID, label: str) -> None:
    """Rename through the roster's own use case, with SCIM's refusals."""
    try:
        await service_groups.rename_group(session, org_id, group_id, label=label)
    except errors.GroupNotFound as exc:
        raise errors.ScimResourceNotFound() from exc
    except errors.GroupExists as exc:
        raise errors.ScimUniqueness() from exc


async def _set_members(
    session: AsyncSession, org_id: uuid.UUID, group_id: uuid.UUID, member_ids: list[str]
) -> None:
    """Replace a group's members; an id that is not one of this roster's trainees is refused."""
    try:
        trainee_ids = [uuid.UUID(member_id) for member_id in member_ids]
        await service_groups.set_group_members(session, org_id, group_id, trainee_ids=trainee_ids)
    except ValueError as exc:
        raise errors.ScimError("A member value is not a user id") from exc
    except errors.TraineeNotFound as exc:
        raise errors.ScimError("A member is not a user on this roster") from exc
    except errors.GroupNotFound as exc:
        raise errors.ScimResourceNotFound() from exc


def _user(trainee: Trainee, base_url: str) -> ScimUser:
    """A trainee as SCIM reads it."""
    display = " ".join(part for part in (trainee.first_name, trainee.last_name) if part) or None
    return ScimUser(
        schemas=[domain_scim.USER_SCHEMA],
        id=trainee.id,
        user_name=trainee.email,
        name=ScimName(given_name=trainee.first_name, family_name=trainee.last_name),
        display_name=display,
        emails=[ScimEmail(value=trainee.email, primary=True, type="work")],
        active=trainee.access_revoked_at is None,
        meta=ScimMeta(
            resource_type="User",
            location=f"{base_url}/Users/{trainee.id}",
            created=trainee.created_at,
            last_modified=trainee.updated_at,
        ),
    )


async def _group(
    session: AsyncSession, org_id: uuid.UUID, group_id: uuid.UUID, label: str, base_url: str
) -> ScimGroup:
    """A trainee group, with its members, as SCIM reads it."""
    member_ids = await _member_ids(session, org_id, group_id)
    return ScimGroup(
        schemas=[domain_scim.GROUP_SCHEMA],
        id=group_id,
        display_name=label,
        members=[ScimMember(value=str(member_id)) for member_id in member_ids],
        meta=ScimMeta(resource_type="Group", location=f"{base_url}/Groups/{group_id}"),
    )


def _token_read(token: ScimToken) -> ScimTokenRead:
    """A stored token as the admin screen lists it."""
    return ScimTokenRead(
        id=token.id,
        label=token.label,
        token_prefix=token.token_prefix,
        created_at=token.created_at,
        last_used_at=token.last_used_at,
        revoked_at=token.revoked_at,
    )
