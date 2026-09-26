"""Storage for an organisation's sso arrangement and its host/email
bindings."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.sso.models import OrganizationSso, OrganizationSsoBinding


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
