"""The ways a request for exam access can be refused."""

from __future__ import annotations

from app.core.errors import Conflict, Forbidden, InvalidInput, NotFound


class InvalidPracticeEmail(InvalidInput):
    """The address given for practice access is not an email address. The bulk route reports
    the same thing per row as the outcome `invalid_email` instead of refusing the batch."""

    code = "invalid_email"
    default_message = "That is not a valid email address"


class PracticeAccessExists(Conflict):
    """This person already holds live practice access to this exam from this organisation.
    The bulk route reports it per row as the outcome `already_active`."""

    code = "practice_access_exists"
    default_message = "That person already has practice access to this exam"


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
    default_message = "We couldn't find that exam"


class EntitlementNotFound(NotFound):
    """No entitlement row with this id, for a platform or org admin acting on
    one that was never granted or has since gone."""

    code = "entitlement_not_found"
    default_message = "We couldn't find that entitlement in this organisation"
