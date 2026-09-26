from __future__ import annotations

from app.core.errors import Forbidden, NotFound


class NotEntitled(Forbidden):
    """No live grant and no trial left. One code whatever the reason, with the detail in
    `details`: the client shows an upgrade prompt either way."""

    code = "not_entitled"
    default_message = "You do not have access to this exam"


class GranteeNotFound(NotFound):
    """No account for the address an institution named. Shares its code with `tenancy` and
    `identity`, since the frontend switches on the code."""

    code = "user_not_found"
    default_message = "No account for that email address"


class UnknownExamError(NotFound):
    """Mirrors `catalog.errors.UnknownExamError`; the code is the shared contract."""

    code = "unknown_exam"
    default_message = "No such exam"


class EntitlementNotFound(NotFound):

    code = "entitlement_not_found"
    default_message = "No such entitlement in this organisation"
