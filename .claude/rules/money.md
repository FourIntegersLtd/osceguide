---
paths:
  - "api/app/features/{entitlements,billing,growth}/**"
  - "api/scripts/{grant_exam_access,seed_partner_attribution,seed_partner_attribution_data}.py"
  - "web/src/capabilities/{account,attribution-dashboard}/**"
  - "web/src/domains/partner/**"
  - "web/src/app/billing/**"
  - "web/src/app/staff/{billing,growth,referral-payouts}/**"
---
# Money: what to know

Owner: `access-owner` (partner screens: `institution-owner`; staff queues: `staff-console-owner`).
Proof: `verify-access`. Anything that moves money also gets the `reviewer` agent (opus).

- **Entitlement grants are not live grants.** `entitlements.list_for_user` returns revoked and
  expired rows too. A gate must filter on `live` and fail closed. Entitlement is not payment
  (ADR 0012): a grant can come from a plan, a partner, a referral or staff.
- Billing: plans, the Stripe webhook ledger, invoices and receipts. The webhook is a ledger
  that records failures (migration `billing_event_failure`); checkout carries the price id
  (`tests/security/test_checkout_carries_price_id.py`). No test sends a live webhook: say so.
- **No Stripe subscriptions.** Checkout is `mode=payment` (pinned in `test_checkout_carries_price_id.py`):
  nothing renews, so closing an account has nothing in Stripe to cancel (A-34). Switching to
  `subscription` means `close_account` must cancel first.
- Receipts have an oracle (`tests/unit/test_receipt_oracle.py`); never edit it to pass.
- Growth: referrals, partner attribution, spend and payouts. Activation and clawback rules
  live in `growth/domain.py`.
- Plans need an exam code (`plans_exam_code_not_null`); an unowned plan is a bug.
- Payments copy says "plan" and "one-off payment", never "subscription", and names no courses
  (there are none). The current plan comes from `currentPlanView` in `account/access.ts`
  (purchase, then organisation grant, then live trial, then free); keep screens on it. It reads
  live grants, never `receipts[0]`: the newest receipt can be a queued plan or a refunded one.
- Web: `capabilities/account` is the learner's plan, billing and referral screens;
  `capabilities/attribution-dashboard` and `domains/partner` are the partner's numbers.
- A partner's wrong numbers: check attribution rows and the spend tests before the screen.
- Hire and partner get journeys (`docs/CORE-JOURNEYS.md`), not their own notes.
