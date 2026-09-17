# The receipt document is the last piece

All twelve oracles are ported and green; `docs/STATUS.md` lists them. What is
left of the fifth one is the document itself. Delete this file when it is done.

## What exists

`receipt_id`, a frozen `customer_email`/`customer_name`, `amount_tax_pence` and
the plan window are written onto `payments` when the Stripe webhook records the
payment (migration `e2f3a4b5c6d7`), and read back through `GET /me/receipts` and
`GET /me/receipts/{receipt_id}`, scoped to the person who paid. Every field is
rendered for display by `app/features/billing/receipts.py`, which is the ported
half of b2c's receipt.

## What is left

1. **Render and send it.** b2c emails the receipt on payment and offers a
   download. Render behind the existing `EmailSender` port, and add byte-level
   goldens for the document — `b2c-api/b2c/tests/unit/test_receipt_document.py`
   is the oracle.
2. **Backfill.** `receipt_id` is null for payments taken before this. Decide
   whether to mint ids for them or leave them Stripe-only. A test pins the
   current behaviour: they are not listed.

## Two divergences still open as product questions

Pinned by `tests/contract/test_feedback_model_parity.py`, not bugs:
SCA's `score_explanation` description (b2b tells the marker to call the
candidate "the doctor" and spells "behaviours"; b2c does neither), and one
sentence sitting in a different position in the shared user prompt.
