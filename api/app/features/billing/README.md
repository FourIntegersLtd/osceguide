# billing

## Purpose
Taking payment and turning it into access. Owns plans, the Stripe webhook
ledger and payment records; writes entitlements through the `entitlements`
service and never grants access itself.

## Use cases
- As a **consumer**, I see what each plan costs and how long it lasts.
- As a **consumer**, I pay and get access for the plan's duration.
- As the **platform**, I apply each Stripe delivery exactly once.
- As **support**, I can see what a customer paid and what it granted.

## Aggregates & invariants
**Plan** and **Payment** stand alone; **StripeEvent** is the idempotency ledger.

- What a customer bought is decided by the Stripe **price id**, not by matching
  the pence amount. b2c matches the amount against a hardcoded table and raises
  on a miss, so a price change, another currency or a coupon breaks the purchase
  after the card has been charged.
- Every delivery is recorded before it is applied, and a repeat is a no-op.
  Stripe retries until it receives a 2xx; without the ledger a retry re-grants.
- Events we do not act on are acknowledged, not errored — answering non-2xx just
  asks Stripe to keep sending them.
- Ledger row, payment and entitlement commit in one transaction, so a crash
  cannot leave someone charged without access or granted twice.
- A payment for an unknown email fails loudly and leaves the event recorded and
  unprocessed, so it can be reconciled rather than lost.
- `mode='payment'`, not Stripe Subscriptions: these are fixed-term purchases and
  the entitlement model already expresses that.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/billing/plans` | none | the pricing page reads this |
| POST | `/api/v1/billing/webhooks/stripe` | signature | `already_applied` / `ignored` / `applied` |
| GET | `/api/v1/me/receipts` | bearer | this person's receipt ids, newest first |
| GET | `/api/v1/me/receipts/{receipt_id}` | bearer | one receipt, every field rendered for display; `receipt_not_found` (404) |

A receipt is scoped to the person who paid. The id is short and printed on a
document that gets forwarded to an accountant or an employer, so holding it is
not enough to read it.

## Jobs
None yet. The receipt is minted and readable; nothing emails it. Rendering and
sending belong behind the existing `EmailSender` port, with byte-level goldens
against `b2c-api/b2c/tests/unit/test_receipt_document.py`.

## Cross-slice dependencies
Calls `entitlements` to grant access and `identity` to resolve the payer.
Signatures are verified in `signature.py` against `STRIPE_WEBHOOK_SECRET`.
