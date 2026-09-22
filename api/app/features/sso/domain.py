"""How a browser finds out that an organisation signs in somewhere else.

The retiring client answered this in the bundle:

    const PARTNER_SSO_HOSTS = ["bmj.osceguide.com"];

— a hostname allow-list shipped to every visitor, with the tenant slug, the
button's wording and the "no password form here" rule beside it. Adding a
partner meant a frontend deploy, and any of the three could disagree with what
the backend actually did.

So the rules live here and the facts live in two tables. Nothing in this module
verifies anybody: it decides which organisation a visitor belongs to and what
their sign-in page should say. Who checks the identity is a separate question —
Clerk has a login behind it (`service_login`, `clerk.py`); direct OIDC to Entra
is still open. See S-1 in `docs/OPEN-QUESTIONS.md`.
"""

from __future__ import annotations

from enum import StrEnum


class Provider(StrEnum):
    """Who will vouch for the identity.

    Named before one is built so a stored row says what it expects rather than
    implying whatever the code happens to do. `clerk` is what the retiring
    backend brokered through; `entra` is Microsoft directly.
    """

    CLERK = "clerk"
    ENTRA = "entra"


class BindingKind(StrEnum):
    """The two ways a visitor is recognised before they have signed in.

    A **host** is a white-label site: everybody who arrives at it belongs to
    that organisation, so the page can be theirs before anybody types anything.

    An **email domain** is home-realm discovery on the ordinary sign-in page:
    somebody types their address and is sent to their own institution instead
    of being asked for a password we will refuse.
    """

    HOST = "host"
    EMAIL_DOMAIN = "email_domain"


class InvalidBinding(Exception):
    pass


class InvalidProvider(Exception):
    pass


class SsoNotConfigurable(Exception):
    pass


MAX_BINDING = 253  # A DNS name's limit, which bounds both kinds.


def normalise_provider(value: str) -> Provider:
    try:
        return Provider((value or "").strip().lower())
    except ValueError as exc:
        raise InvalidProvider(
            f"{value!r} is not a provider this platform knows: {', '.join(Provider)}."
        ) from exc


def normalise_host(value: str) -> str:
    """A bare hostname, however it was typed.

    People paste URLs into configuration fields. Storing `https://bmj.osceguide.com/`
    would mean a lookup by `Host:` header never matches it, and the failure is
    invisible: the partner's site silently shows the ordinary sign-in page.
    """
    text = (value or "").strip().lower()
    for prefix in ("https://", "http://"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
    text = text.split("/", 1)[0]
    text = text.split(":", 1)[0]  # A port is not part of the identity.
    text = text.strip(".")
    _ensure_name(text, "A host")
    return text


def normalise_email_domain(value: str) -> str:
    """The domain half, whether they typed a domain or a whole address."""
    text = (value or "").strip().lower()
    if "@" in text:
        text = text.rsplit("@", 1)[1]
    text = text.strip(".")
    _ensure_name(text, "An email domain")
    return text


def _ensure_name(text: str, what: str) -> None:
    if not text:
        raise InvalidBinding(f"{what} cannot be empty.")
    if len(text) > MAX_BINDING:
        raise InvalidBinding(f"{what} is at most {MAX_BINDING} characters.")
    if " " in text:
        raise InvalidBinding(f"{what} cannot contain spaces.")
    # `localhost` is the one bare name worth allowing, for development.
    if "." not in text and text != "localhost":
        raise InvalidBinding(f"{what} must be a dotted name, not {text!r}.")


def normalise_binding(kind: BindingKind, value: str) -> str:
    return normalise_host(value) if kind is BindingKind.HOST else normalise_email_domain(value)


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
