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
- As the **platform**, I invoice an organisation, and mark the invoice paid or void.
- As an **organisation admin**, I read my organisation's invoices and quote our
  purchase order number on one we have not yet paid.

## Aggregates & invariants
**Plan** and **Payment** stand alone; **StripeEvent** is the idempotency ledger;
**Invoice** owns its **InvoiceLine**s.

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
- A payment whose address matches no account is acknowledged (200
  `needs_attention`, never a 4xx: Stripe would retry for three days and then
  drop it) and left unprocessed with a `failure`, in the reconcile queue
  (`/platform/billing/events?failed_only=true`). Support replays it once the
  person registers, or records it against the right account with the intent id.
- `mode='payment'`, not Stripe Subscriptions: these are fixed-term purchases and
  the entitlement model already expresses that.
- An invoice number is `INV-<year>-<n>` from a Postgres sequence: never shared by
  two invoices raised at once, never reused, void ones included.
- An invoice is `issued`, then `paid` or `void`, and those two are final. The PO
  number may be set or corrected only while it is `issued`.
- A line may name a settled payment (`service_settlement`, typically a bank
  transfer entered in the console); it then bills that payment's total and is
  described by the plan it bought unless told otherwise.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/billing/plans` | none | the pricing page reads this |
| POST | `/api/v1/billing/checkout` | bearer | Start paying for a plan by code; `plan_not_available` (404), `already_purchased` (409: a live paid purchase of that exam; a trial, an org grant or a lapsed purchase does not block), `checkout_failed` (503). `Idempotency-Key` is passed to Stripe scoped to the buyer. Grants nothing — the webhook does |
| POST | `/api/v1/billing/webhooks/stripe` | signature | `already_applied` / `ignored` / `applied` |
| GET | `/api/v1/me/receipts` | bearer | this person's receipt ids, newest first |
| GET | `/api/v1/me/receipts/{receipt_id}` | bearer | one receipt, every field rendered for display; `receipt_not_found` (404) |
| GET | `/api/v1/me/receipts/{receipt_id}/document` | bearer | The receipt as HTML, to print or keep |
| GET | `/api/v1/platform/users/{id}/payments` | platform admin | this person's payments with what each bought; `user_not_found` (404) |
| GET | `/api/v1/platform/users/{id}/billing-events` | platform admin | every webhook delivery naming their address, applied or refused |
| GET | `/api/v1/platform/billing/events` | platform admin | the ledger, newest first; `?failed_only=true` is the reconcile queue |
| GET | `/api/v1/platform/billing/plans` | platform admin | every plan priced, on sale or retired, with its referral price |
| POST | `/api/v1/platform/billing/plans` | platform admin | price a published platform exam: creates both Stripe prices and the plan plus its 10%-off `_referral` twin; `plan_code_taken` (409), `unknown_exam` (404), `price_creation_failed` (503) |
| PATCH | `/api/v1/platform/billing/plans/{plan_code}` | platform admin | `active` on or off for the plan and its twin. Retiring stops new checkouts only: the webhook resolves prices across every plan, so a payment under way still grants. Back on sale only for a published exam (`unknown_exam`) |
| POST | `/api/v1/platform/organizations/{org_slug}/invoices` | platform admin | raise an invoice; `invalid_invoice_line` (422) |
| PATCH | `/api/v1/platform/invoices/{invoice_id}` | platform admin | `status` `paid`/`void`, `po_number`; `invoice_not_editable` (409) |
| GET | `/api/v1/orgs/{org_slug}/invoices` | org admin | newest first, with lines |
| GET | `/api/v1/orgs/{org_slug}/invoices/{invoice_id}` | org admin | `invoice_not_found` (404) |
| PUT | `/api/v1/orgs/{org_slug}/invoices/{invoice_id}/po-number` | org admin | `invoice_not_editable` (409) once paid or void |

A receipt is scoped to the person who paid. The id is short and printed on a
document that gets forwarded to an accountant or an employer, so holding it is
not enough to read it.

## Jobs
None yet. The receipt is minted and readable; nothing emails it. Rendering and
sending belong behind the existing `EmailSender` port, with byte-level goldens
against `b2c-api/b2c/tests/unit/test_receipt_document.py`.

## Cross-slice dependencies
Calls `entitlements` to grant access, `identity` to resolve the payer, and
`tenancy` to name the organisation an invoice is for.
Signatures are verified in `signature.py` against `STRIPE_WEBHOOK_SECRET`.
