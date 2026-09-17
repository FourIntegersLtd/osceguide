from __future__ import annotations

from app.core.errors import AppError, Conflict, InvalidInput, NotFound


class UnknownPlanError(NotFound):
    """A charged payment with nothing to grant.

    `persist_effects`: the ledger row and the reason it failed survive the
    refusal, so the payment is recoverable by hand or by Stripe's retry once a
    plan row exists. Raised before anything is granted, so nothing partial can
    be kept.
    """

    code = "unknown_plan"
    default_message = "No plan for that price"
    persist_effects = True


class InvalidSignature(AppError):
    status = 400
    code = "invalid_signature"
    default_message = "That webhook could not be verified"


class PaymentAlreadyRecorded(Conflict):
    code = "payment_already_recorded"
    default_message = "That payment has already been applied"


class InvalidWebhook(InvalidInput):
    """The delivery could not be applied.

    `persist_effects` for the same reason as `UnknownPlanError`: a payment for
    an address with no account must leave its ledger row behind. Every raise
    of this precedes any grant.
    """

    code = "invalid_webhook"
    default_message = "That webhook payload was not usable"
    persist_effects = True


class UnknownExamError(NotFound):
    """Mirrors `catalog.errors.UnknownExamError`, and shares its code.

    A plan names an exam by code, and the code is a plain string rather than a
    foreign key — deliberately, so a plan can be created before the exam is.
    An exam that is retired, or never written, therefore surfaces here when the
    purchase is granted. It became reachable once exams stopped being four
    seeded rows.
    """

    code = "unknown_exam"
    default_message = "No such exam"


class ReceiptNotFound(NotFound):
    """No such receipt of yours.

    Indistinguishable from one that does not exist: receipt ids are short and
    travel on forwarded documents, so probing must tell somebody nothing.
    """

    code = "receipt_not_found"
    default_message = "No such receipt"
