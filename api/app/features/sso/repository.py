"""Storage for an organisation's sso arrangement and its host/email
bindings."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.sso.models import OrganizationSamlConnection, OrganizationSso, OrganizationSsoBinding


async def config_for_org(session: AsyncSession, org_id: uuid.UUID) -> OrganizationSso | None:
    """This organisation's arrangement, or None if it has never configured one."""
    config_result = await session.execute(select(OrganizationSso).where(OrganizationSso.org_id == org_id))
    return config_result.scalar_one_or_none()


async def bindings_for(session: AsyncSession, sso_id: uuid.UUID) -> Sequence[OrganizationSsoBinding]:
    """Every host and email domain this configuration claims, in a stable order."""
    bindings_result = await session.execute(
        select(OrganizationSsoBinding)
        .where(OrganizationSsoBinding.sso_id == sso_id)
        .order_by(OrganizationSsoBinding.kind, OrganizationSsoBinding.value)
    )
    return bindings_result.scalars().all()


async def find_by_binding(session: AsyncSession, *, kind: str, binding_value: str) -> OrganizationSso | None:
    """The lookup the sign-in page makes, by host or by email domain.

    Answers this slice's row and not the organisation: `organizations` belongs
    to `tenancy`, and the name a button needs is asked of that slice's service.
    The binding is unique across the platform, so there is no ordering to
    decide and nothing to disambiguate.
    """
    config_result = await session.execute(
        select(OrganizationSso)
        # From the binding outwards: it is the row being looked up.
        .select_from(OrganizationSsoBinding)
        .join(OrganizationSso, OrganizationSso.id == OrganizationSsoBinding.sso_id)
        .where(OrganizationSsoBinding.kind == kind, OrganizationSsoBinding.value == binding_value)
    )
    return config_result.scalar_one_or_none()


async def binding_owner(session: AsyncSession, *, kind: str, binding_value: str) -> uuid.UUID | None:
    """Which configuration already claims this, if any."""
    owner_result = await session.execute(
        select(OrganizationSsoBinding.sso_id).where(
            OrganizationSsoBinding.kind == kind, OrganizationSsoBinding.value == binding_value
        )
    )
    return owner_result.scalar_one_or_none()


async def upsert_config(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    provider: str,
    issuer: str | None,
    enabled: bool,
    sso_only: bool,
    sign_in_label: str | None,
    default_exam_code: str | None,
) -> OrganizationSso:
    """Create this organisation's arrangement if it has none, or overwrite
    every field of the one it already has — a save is always a full
    replace, never a partial patch."""
    config = await config_for_org(session, org_id)
    if config is None:
        config = OrganizationSso(org_id=org_id)
        session.add(config)
    config.provider = provider
    config.issuer = issuer
    config.enabled = enabled
    config.sso_only = sso_only
    config.sign_in_label = sign_in_label
    config.default_exam_code = default_exam_code
    await session.flush()
    return config


async def replace_bindings(
    session: AsyncSession, *, sso_id: uuid.UUID, bindings: Sequence[tuple[str, str]]
) -> None:
    """The saved set becomes exactly what was sent.

    A replace rather than a merge because the screen sends the whole list, and
    a merge would make removing a hostname impossible without another route.
    """
    await session.execute(delete(OrganizationSsoBinding).where(OrganizationSsoBinding.sso_id == sso_id))
    for kind, binding_value in bindings:
        session.add(OrganizationSsoBinding(sso_id=sso_id, kind=kind, value=binding_value))
    await session.flush()


async def saml_connection_for_org(
    session: AsyncSession, org_id: uuid.UUID
) -> OrganizationSamlConnection | None:
    """This organisation's SAML connection, or None."""
    stmt = select(OrganizationSamlConnection).where(OrganizationSamlConnection.org_id == org_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def saml_connection_by_id(
    session: AsyncSession, connection_id: uuid.UUID
) -> OrganizationSamlConnection | None:
    """A SAML connection by its public id. Not org-scoped: the id is what an IdP posts to."""
    stmt = select(OrganizationSamlConnection).where(OrganizationSamlConnection.id == connection_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def save_saml_connection(
    session: AsyncSession, org_id: uuid.UUID, **values: Any
) -> OrganizationSamlConnection:
    """Write this organisation's SAML connection, creating it on first save."""
    stmt = (
        insert(OrganizationSamlConnection)
        .values(id=uuid.uuid4(), org_id=org_id, **values)
        .on_conflict_do_update(
            constraint="uq_organization_saml_connections_org_id", set_={**values, "updated_at": func.now()}
        )
        .returning(OrganizationSamlConnection)
        .execution_options(populate_existing=True)
    )
    return (await session.execute(stmt)).scalar_one()


async def any_sso_only(session: AsyncSession, org_ids: Sequence[uuid.UUID]) -> bool:
    """Whether any of these organisations has switched its members to signing in only through SSO."""
    if not org_ids:
        return False
    stmt = (
        select(OrganizationSso.id)
        .where(OrganizationSso.org_id.in_(list(org_ids)), OrganizationSso.sso_only.is_(True))
        .limit(1)
    )
    return (await session.execute(stmt)).first() is not None
