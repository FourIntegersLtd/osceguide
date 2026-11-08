"""The errors this slice raises. Each `code` is a contract clients branch on, never `message`."""

from __future__ import annotations

from app.core.errors import AppError, Conflict, InvalidInput, NotFound, Unavailable

# Re-exported: checkout refuses a referral code with growth's own error, and the
# router may only name this slice's errors.
from app.features.growth.errors import ReferralNotFound as ReferralNotFound


class EmptyPlanUpdate(InvalidInput):
    """A plan PATCH set neither `active` nor `station_limit`, so there is nothing to change."""

    code = "empty_plan_update"
    default_message = "Change at least one thing: turn access on or off, or set a station limit."


class UnknownPlanError(NotFound):
    """A charged payment with nothing to grant.

    `persist_effects`: the ledger row and the reason it failed survive the refusal, so the
    payment is recoverable by hand or by Stripe's retry once a plan row exists.
    """

    code = "unknown_plan"
    default_message = "No plan for that price"
    persist_effects = True


class InvalidSignature(AppError):
    """The `Stripe-Signature` header did not verify: wrong secret, tampered body, or a replay
    outside the tolerance window (see `signature.verify`)."""

    status = 400
    code = "invalid_signature"
    default_message = "That webhook could not be verified"


class PaymentAlreadyRecorded(Conflict):
    """A manual payment with this reference has already been recorded once. Recording it again
    would grant access twice for one purchase."""

    code = "payment_already_recorded"
    default_message = "That payment has already been applied"


class InvalidWebhook(InvalidInput):
    """The delivery could not be applied.

    `persist_effects` for the same reason as `UnknownPlanError`: a payment for an address with
    no account must leave its ledger row behind.
    """

    code = "invalid_webhook"
    default_message = "That webhook payload was not usable"
    persist_effects = True


class UnknownExamError(NotFound):
    """Mirrors `catalog.errors.UnknownExamError`, and shares its code.

    A plan names an exam by code, a plain string rather than a foreign key, so a plan can be
    created before the exam is. A retired or never-written exam surfaces here when granted.
    """

    code = "unknown_exam"
    default_message = "We couldn't find that exam"


class ReceiptNotFound(NotFound):
    """No such receipt of yours — indistinguishable from one that does not exist, since receipt
    ids are short and travel on forwarded documents, so probing must tell somebody nothing."""

    code = "receipt_not_found"
    default_message = "We couldn't find that receipt"


class AlreadyPurchased(Conflict):
    """The buyer already holds this plan, running or bought to start. A second payment for the same
    plan would buy access they have; a different plan is allowed and extends it."""

    code = "already_purchased"
    default_message = (
        "You already have this plan. Choose a different plan to extend your access, "
        "or buy it again when it ends."
    )


class PlanNotAvailable(NotFound):
    """No such plan, or one that is no longer sold. Not `unknown_plan`, which means a *charged*
    payment with nothing to grant — a different emergency."""

    code = "plan_not_available"
    default_message = "That plan is not available"


class PlanNotFound(NotFound):
    """No full-price plan with that code, on sale or not. A referral twin is managed through
    the plan it discounts, so its own code is not found here either."""

    code = "plan_not_found"
    default_message = "We couldn't find that plan"


class PlanCodeTaken(Conflict):
    """A plan, or its referral twin, already has this code. Codes are never reused: a payment
    names its plan by code for good."""

    code = "plan_code_taken"
    default_message = "A plan already has that code"


class PriceCreationFailed(Unavailable):
    """Stripe could not create the price, so no plan was written. 503: usually transient, or
    this deployment has no Stripe key."""

    code = "price_creation_failed"
    default_message = "Stripe could not create that price. Try again in a moment."


class StripeRefundFailed(Unavailable):
    """Stripe did not refund the payment, so nothing was withdrawn: the money and the access
    are as they were. 503: usually transient, or this deployment has no Stripe key."""

    code = "stripe_refund_failed"
    default_message = "Stripe could not refund that payment. Nothing has changed; try again in a moment."


class PaymentAlreadyRefunded(Conflict):
    """Access for this payment was already withdrawn, a refund was recorded, or it was disputed.
    Refusing before Stripe is asked stops a second click or a stale console refunding twice."""

    code = "payment_already_refunded"
    default_message = (
        "That payment has already been refunded, withdrawn or disputed, so it was not refunded again."
    )


class StripeRefundRefused(Conflict):
    """Stripe answered and refused (already refunded there, disputed, too old). Not an outage: the
    reason is Stripe's own, and nothing has changed here."""

    code = "stripe_refund_refused"
    default_message = "Stripe refused that refund."


class NotAStripePayment(Conflict):
    """The payment was recorded by hand, so there is no Stripe charge to refund. Withdraw its access
    with "Record refund" and return the money where it was taken."""

    code = "not_a_stripe_payment"
    default_message = "That payment did not go through Stripe, so there is nothing to refund there."


class ReferralDiscountUnavailable(NotFound):
    """The code is fine, but this plan has no referral price to switch to. Refused rather than
    charged in full: the customer typed a code expecting 10% off."""

    code = "referral_discount_unavailable"
    default_message = "That plan has no referral discount"


class CheckoutFailed(Unavailable):
    """The card processor could not start a checkout. 503 rather than 500: it is often
    transient, and the client should say "try again" rather than "something is broken"."""

    code = "checkout_failed"
    default_message = "We could not start the checkout. Try again in a moment."


class PayerNotFound(NotFound):
    """No such account. The code every slice answers with for a missing person."""

    code = "user_not_found"
    default_message = "We couldn't find that account"


class BillingEventNotFound(NotFound):
    """No webhook delivery with that id is on the ledger, so there is nothing to replay."""

    code = "billing_event_not_found"
    default_message = "We couldn't find that webhook delivery"


class PaymentNotFound(NotFound):
    """No payment with that id, so there is nothing to refund."""

    code = "payment_not_found"
    default_message = "We couldn't find that payment"


class PaymentNotYetRecorded(NotFound):
    """A refund or dispute named a charge with no payment yet (its checkout may still be on the
    way). `persist_effects`: the ledger row and its failure survive, so it is in `failed_only`
    and Stripe's retry applies it once the payment exists."""

    code = "payment_not_yet_recorded"
    default_message = "No payment is recorded for that charge yet"
    persist_effects = True


class InvoiceNotFound(NotFound):
    """No invoice by that id belongs to this organisation."""

    code = "invoice_not_found"
    default_message = "We couldn't find that invoice"


class InvoiceNotEditableError(Conflict):
    """The invoice is paid or void, and a final invoice is not changed."""

    code = "invoice_not_editable"
    default_message = "That invoice is final and cannot be changed"


class InvalidInvoiceLineError(InvalidInput):
    """A line needs an amount, or a payment of this organisation's to take one from."""

    code = "invalid_invoice_line"
    default_message = "Each line needs an amount, or a payment to bill for"
