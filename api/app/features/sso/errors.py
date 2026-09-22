from __future__ import annotations

from app.core.errors import Conflict, InvalidInput, NotFound, Unavailable


class SsoNotConfigured(NotFound):
    code = "sso_not_configured"
    default_message = "That organisation does not sign in through an identity provider"


class SsoLoginUnavailable(Unavailable):
    """No broker is configured, or it could not be reached.

    Fails closed, like the worker guard and Stripe: an unset secret or an
    unreachable provider refuses the sign-in rather than trusting anything.
    """

    code = "sso_login_unavailable"
    default_message = "Sign-in through an identity provider is not available here"


class SsoProviderUnsupported(Unavailable):
    """The organisation's provider is known but has no flow built here.

    `Provider` names `entra` so a stored row can say what it expects; only
    Clerk has a login behind it. Its own code rather than `sso_not_configured`
    because the arrangement exists — the platform just cannot honour it yet.
    """

    code = "sso_provider_unsupported"
    default_message = "That organisation's sign-in provider is not enabled here"


class SsoVerificationFailed(InvalidInput):
    """The broker did not vouch for the token the callback was handed.

    `invalid_input` (422) rather than 401: nobody is signed in to be
    unauthenticated, and the client's next move is to send the person back to
    the broker, which is what it does for a malformed request.
    """

    code = "sso_verification_failed"
    default_message = "That sign-in could not be verified. Try again."


class InvalidSsoBinding(InvalidInput):
    code = "invalid_sso_binding"
    default_message = "That is not a usable hostname or email domain"


class UnknownSsoProvider(InvalidInput):
    code = "unknown_sso_provider"
    default_message = "That is not an identity provider this platform knows"


class SsoNotConfigurableError(InvalidInput):
    code = "sso_not_configurable"
    default_message = "That combination of settings would leave nobody a way in"


class SsoBindingTaken(Conflict):
    code = "sso_binding_taken"
    default_message = "Another organisation already claims that host or email domain"
