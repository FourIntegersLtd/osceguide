"""Reading and writing an organisation's sign-in arrangement.

The read is public and the write is platform-admin, deliberately: whoever
controls the issuer controls who may sign in as that institution's members.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, raise_mapped
from app.core.tenancy import OrgNotFound
from app.features.identity import service as identity
from app.features.sso import domain, errors, repository, schemas
from app.features.sso.models import OrganizationSso
from app.features.tenancy import service as tenancy

_REFUSALS: dict[type[Exception], type[AppError]] = {
    domain.InvalidBinding: errors.InvalidSsoBinding,
    domain.InvalidProvider: errors.UnknownSsoProvider,
    domain.SsoNotConfigurable: errors.SsoNotConfigurableError,
}


async def sign_in_for_host(session: AsyncSession, host: str) -> schemas.SsoSignIn | None:
    """What the sign-in page on a white-label host should show; `None` for a host with no SSO."""
    try:
        binding_value = domain.normalise_host(host)
    except domain.InvalidBinding as exc:
        raise_mapped(exc, _REFUSALS)
    return await _sign_in(session, kind=domain.BindingKind.HOST, binding_value=binding_value)


async def sign_in_for_email(session: AsyncSession, email: str) -> schemas.SsoSignIn | None:
    """Home-realm discovery: where this address signs in, if not here.

    `None` for an address nobody claims, and a refusal for something that is not
    an address, because "no SSO here" and "that is not an address" are
    different things and the page behaves differently for each.
    """
    binding_value = domain.domain_of(email)
    if not binding_value:
        raise errors.InvalidSsoBinding("That is not an email address.")
    return await _sign_in(session, kind=domain.BindingKind.EMAIL_DOMAIN, binding_value=binding_value)


async def _sign_in(
    session: AsyncSession, *, kind: domain.BindingKind, binding_value: str
) -> schemas.SsoSignIn | None:
    """Look a binding up and answer what its sign-in page should show, or
    `None` ("sign in here, with a password") — for no such binding, a disabled
    configuration, and an organisation that no longer exists alike, since
    none of those is something to explain to an anonymous caller.

    `None` rather than a 404: no SSO is what nearly every host answers, and a
    404 on every visit to `/login` read as a fault in every browser console."""
    config = await repository.find_by_binding(session, kind=kind.value, binding_value=binding_value)
    if config is None:
        return None
    # A configuration that exists but is switched off is not something to tell
    # an anonymous caller about: the answer is the same as never having had one.
    if not config.enabled:
        return None
    # The organisation's name belongs to `tenancy`; this slice asks for it
    # rather than reading its table.
    org = await tenancy.org_ref_by_id(session, config.org_id)
    if org is None:
        return None
    provider = domain.normalise_provider(config.provider)
    return schemas.SsoSignIn(
        org_slug=org.slug,
        org_name=org.name,
        provider=provider.value,
        sign_in_label=domain.sign_in_label(config.sign_in_label, provider),
        sso_only=config.sso_only,
        default_exam_code=config.default_exam_code,
    )


async def read_config(session: AsyncSession, org_slug: str) -> schemas.SsoConfigRead | None:
    """The whole arrangement for the platform console. `None` for an organisation
    with no arrangement yet (the ordinary case, not an error); an unknown org
    is refused `org_not_found`."""
    org = await tenancy.org_ref_by_slug(session, org_slug)
    if org is None:
        raise OrgNotFound()
    config = await repository.config_for_org(session, org.id)
    if config is None:
        return None
    return await _read(session, config, org_slug=org.slug)


async def save_config(
    session: AsyncSession, org_slug: str, body: schemas.SaveSsoConfig
) -> schemas.SsoConfigRead:
    """Replace this organisation's arrangement wholesale.

    Refuses before writing anything for a provider nobody knows, a setting
    combination `domain.ensure_configurable` calls unsafe, or a host or email
    domain another organisation already claims — the last checked binding by
    binding, so the refusal names the one to go and sort out.
    """
    org = await tenancy.org_ref_by_slug(session, org_slug)
    if org is None:
        raise OrgNotFound()

    try:
        provider = domain.normalise_provider(body.provider)
        issuer = (body.issuer or "").strip() or None
        domain.ensure_configurable(enabled=body.enabled, sso_only=body.sso_only, issuer=issuer)
        bindings = _bindings(body)
    except Exception as exc:  # noqa: BLE001 - mapped above
        raise_mapped(exc, _REFUSALS)

    await _ensure_nobody_is_locked_out(session, org.id, body)
    config = await repository.upsert_config(
        session,
        org_id=org.id,
        provider=provider.value,
        issuer=issuer,
        enabled=body.enabled,
        sso_only=body.sso_only,
        sign_in_label=(body.sign_in_label or "").strip() or None,
        default_exam_code=(body.default_exam_code or "").strip() or None,
    )

    # Checked before writing rather than caught as a constraint violation, so
    # the refusal names the host somebody has to go and sort out.
    for kind, binding_value in bindings:
        owner = await repository.binding_owner(session, kind=kind, binding_value=binding_value)
        if owner is not None and owner != config.id:
            raise errors.SsoBindingTaken(f"{binding_value} is already claimed by another organisation.")

    await repository.replace_bindings(session, sso_id=config.id, bindings=bindings)
    return await _read(session, config, org_slug=org.slug)


async def _ensure_nobody_is_locked_out(
    session: AsyncSession, org_id: uuid.UUID, body: schemas.SaveSsoConfig
) -> None:
    """Switching to SSO-only hides the password form: refuse, naming the members who have only a
    password, unless the admin has seen them and confirmed. Already SSO-only changes nothing for them."""
    if not (body.enabled and body.sso_only) or body.confirm_password_members:
        return
    current = await repository.config_for_org(session, org_id)
    if current is not None and current.sso_only:
        return
    seated = await identity.emails_with_passwords(
        session, await tenancy.live_member_user_ids(session, org_id)
    )
    if seated:
        raise errors.SsoOnlyLocksOutPasswordMembers(details={"count": len(seated), "emails": seated[:20]})


def _bindings(body: schemas.SaveSsoConfig) -> list[tuple[str, str]]:
    """Every host and domain, normalised, in a stable order, without repeats."""
    seen: set[tuple[str, str]] = set()
    pairs: list[tuple[str, str]] = []
    for kind, raw_values in (
        (domain.BindingKind.HOST, body.hosts),
        (domain.BindingKind.EMAIL_DOMAIN, body.email_domains),
    ):
        for raw in raw_values:
            pair = (kind.value, domain.normalise_binding(kind, raw))
            if pair in seen:
                continue
            seen.add(pair)
            pairs.append(pair)
    return pairs


async def _read(session: AsyncSession, config: OrganizationSso, *, org_slug: str) -> schemas.SsoConfigRead:
    """Build the console's read shape for one arrangement, its bindings
    loaded alongside it."""
    bindings = await repository.bindings_for(session, config.id)
    provider = domain.normalise_provider(config.provider)
    return schemas.SsoConfigRead(
        org_id=config.org_id,
        org_slug=org_slug,
        provider=provider.value,
        issuer=config.issuer,
        enabled=config.enabled,
        sso_only=config.sso_only,
        sign_in_label=domain.sign_in_label(config.sign_in_label, provider),
        default_exam_code=config.default_exam_code,
        bindings=[schemas.SsoBinding(kind=binding.kind, value=binding.value) for binding in bindings],
    )
