from __future__ import annotations

from app.core.errors import Conflict, InvalidInput, NotFound


class SsoNotConfigured(NotFound):
    code = "sso_not_configured"
    default_message = "That organisation does not sign in through an identity provider"


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
