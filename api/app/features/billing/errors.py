from __future__ import annotations

from app.core.errors import AppError, Conflict, InvalidInput, NotFound


class UnknownPlanError(NotFound):
    code = "unknown_plan"
    default_message = "No plan for that price"


class InvalidSignature(AppError):
    status = 400
    code = "invalid_signature"
    default_message = "That webhook could not be verified"


class PaymentAlreadyRecorded(Conflict):
    code = "payment_already_recorded"
    default_message = "That payment has already been applied"


class InvalidWebhook(InvalidInput):
    code = "invalid_webhook"
    default_message = "That webhook payload was not usable"
