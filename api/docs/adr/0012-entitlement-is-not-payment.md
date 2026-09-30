# 0012. Entitlement is a record of access, separate from the payment that caused it

Date: 2026-09-16
Status: accepted

## Context
Four sources of access exist today and none of them share a shape. A consumer purchase sets
`has_paid` and `plan_end_date` on a Firestore user document — and because a b2c user is four
disjoint documents across four collections, buying SCA grants nothing in PLAB. An institution
grants access through `b2b_practice_entitlements` plus a `b2b_practice_users` row. An SSO tenant
carries its own plan end date. A free trial is not stored at all: it is recomputed on each
request from three conditions (three set stations, three completed attempts, or an account older
than fourteen days).

The Stripe path has two faults that follow from treating the payment as the access. There is no
webhook idempotency, so a Stripe retry re-runs the grant. And the plan is inferred from the
amount paid, matched against hardcoded pence values, raising `ValueError("Invalid amount paid")`
on anything unrecognised — so a price change or a currency variation breaks purchases.

## Decision
`entitlements(user_id, exam_id, source, source_ref, org_id, starts_at, ends_at, revoked_at)`,
append-only, where `source` is one of `purchase`, `org_grant`, `trial`, `sso_tenant`, `admin`.
A payment is a separate record that *grants* an entitlement; `stripe_events` gives the webhook
idempotency, and a `plans` table maps the Stripe price id to a duration instead of guessing from
the amount.

One predicate answers the only question that matters — may this principal attempt this exam now
— and every attempt-creating path calls it. Nothing else reads `has_paid`.

## Consequences
- Consumer and institutional access resolve through the same check while keeping distinct
  sources, so a user who is both a subscriber and a trainee needs no special case.
- Revocation and expiry become data rather than a deletion, so "why could they do that?" is
  answerable after the fact.
- Refunds and disputes revoke an entitlement without deleting the payment record.
- The free-trial rule moves from a request-time recomputation into a `trial` entitlement written
  once, and its current behaviour is ported verbatim as the oracle so nobody's trial changes.
- Stripe retries stop double-granting, and changing a price stops breaking checkout.
