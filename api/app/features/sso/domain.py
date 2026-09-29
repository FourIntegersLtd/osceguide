"""How a browser finds out that an organisation signs in somewhere else.

The rules live here and the facts live in two tables, rather than a
client-side hostname allow-list that a frontend deploy could drift out of
sync with. Nothing in this module verifies anybody: it decides which
organisation a visitor belongs to and what their sign-in page should say.
Who checks the identity is separate — see `service_login`, `clerk.py` and
`entra.py`.
"""

from __future__ import annotations

from enum import StrEnum


class Provider(StrEnum):
    """Who will vouch for the identity.

    Named before one is built so a stored row says what it expects rather
    than implying whatever the code happens to do.
    """

    CLERK = "clerk"
    ENTRA = "entra"
    # SAML 2.0 (E-20): the IdP is an `OrganizationSamlConnection`, and
    # `issuer` holds its entity id.
    SAML = "saml"


class BindingKind(StrEnum):
    """The two ways a visitor is recognised before they have signed in.

    A **host** is a white-label site: everybody who arrives belongs to that
    organisation. An **email domain** is home-realm discovery on the
    ordinary sign-in page: somebody types their address and is sent to
    their own institution instead of a password form we will refuse.
    """

    HOST = "host"
    EMAIL_DOMAIN = "email_domain"


class InvalidBinding(Exception):
    """A host or email domain that fails `_ensure_name`: empty, too long,
    containing a space, or not a dotted name (`localhost` excepted)."""


class InvalidProvider(Exception):
    """A stored or submitted provider string that is not one `Provider`
    knows, at the point something tries to write or trust it."""


class SsoNotConfigurable(Exception):
    """A configuration `ensure_configurable` refuses: SSO-only with SSO
    switched off, or turned on with no issuer."""


MAX_BINDING = 253  # A DNS name's limit, which bounds both kinds.


def normalise_provider(raw_provider: str) -> Provider:
    """The known `Provider` this string names, or refuse.

    Refuses rather than defaulting to a provider, because guessing here would
    mean a typo in a stored value silently pointed sign-in at the wrong
    identity service.
    """
    try:
        return Provider((raw_provider or "").strip().lower())
    except ValueError as exc:
        raise InvalidProvider(
            f"{raw_provider!r} is not a provider this platform knows: {', '.join(Provider)}."
        ) from exc


def normalise_host(raw_host: str) -> str:
    """A bare hostname, however it was typed.

    People paste URLs into configuration fields. Storing `https://bmj.osceguide.com/`
    would mean a lookup by `Host:` header never matches it, and the failure is
    invisible: the partner's site silently shows the ordinary sign-in page.
    """
    text = (raw_host or "").strip().lower()
    for prefix in ("https://", "http://"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
    text = text.split("/", 1)[0]
    text = text.split(":", 1)[0]  # A port is not part of the identity.
    text = text.strip(".")
    _ensure_name(text, "A host")
    return text


def normalise_email_domain(raw_email_domain: str) -> str:
    """The domain half, whether they typed a domain or a whole address."""
    text = (raw_email_domain or "").strip().lower()
    if "@" in text:
        text = text.rsplit("@", 1)[1]
    text = text.strip(".")
    _ensure_name(text, "An email domain")
    return text


def _ensure_name(text: str, what: str) -> None:
    """Refuse a binding that is empty, too long, contains a space, or is not
    a dotted name — the shape rule every host and email domain shares."""
    if not text:
        raise InvalidBinding(f"{what} cannot be empty.")
    if len(text) > MAX_BINDING:
        raise InvalidBinding(f"{what} is at most {MAX_BINDING} characters.")
    if " " in text:
        raise InvalidBinding(f"{what} cannot contain spaces.")
    # `localhost` is the one bare name worth allowing, for development.
    if "." not in text and text != "localhost":
        raise InvalidBinding(f"{what} must be a dotted name, not {text!r}.")


def normalise_binding(kind: BindingKind, raw_value: str) -> str:
    return normalise_host(raw_value) if kind is BindingKind.HOST else normalise_email_domain(raw_value)


def domain_of(email: str) -> str | None:
    """The domain to look a sign-in up by, or None if that was not an address."""
    text = (email or "").strip().lower()
    if "@" not in text:
        return None
    domain = text.rsplit("@", 1)[1].strip(".")
    return domain or None


def ensure_configurable(*, enabled: bool, sso_only: bool, issuer: str | None) -> None:
    """What a stored configuration has to hold together.

    `sso_only` is the dangerous one: it turns the password form off for
    everybody that organisation recognises. Allowing it while SSO is disabled
    would lock an institution out of its own account with one checkbox, and the
    person who did it would find out from their users.
    """
    if sso_only and not enabled:
        raise SsoNotConfigurable(
            "Sign-in cannot be restricted to SSO while SSO is turned off — that leaves nobody a way in."
        )
    if enabled and not (issuer or "").strip():
        raise SsoNotConfigurable("An issuer is required before SSO can be turned on.")


def sign_in_label(label: str | None, provider: Provider) -> str:
    """What the button says.

    A default per provider rather than a required field: every partner so far
    would have typed the same sentence, and an empty label renders as a button
    with no words on it.
    """
    text = (label or "").strip()
    if text:
        return text
    return "Sign in with Microsoft" if provider is Provider.ENTRA else "Sign in with your organisation"
