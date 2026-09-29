# growth

## Purpose
Where users come from: partner attribution and referrals.

Commercial rather than incidental — these numbers decide what a partner is owed,
so the rules are strict and nothing is inferred.

## Use cases
- As a **visitor**, my arrival from a partner link is logged before I have an account.
- As a **new user**, my signup is credited to the partner who sent me.
- As a **partner reporter**, I read my own funnel and nobody else's.
- As a **consumer**, I get a referral code and see what it has earned.
- As a **platform admin**, I check a partner's arrival ledger against Mixpanel's
  landing count for a date range, read the pilot's estimated click spend against
  what the people it sent have paid, and set its cost per click and alerts.
- As the **team**, we are emailed when a pilot's estimated spend crosses a
  threshold, once per threshold.

## Aggregates & invariants
**PartnerArrival**, **Acquisition**, **PartnerReporter**, **Referral** and
**PartnerPilotConfig**.

- A reference we do not recognise credits **nobody**. Guessing is worse than
  declining, because the cost of a wrong guess is money owed to the wrong party.
- The pilot is `bmj` and the exams are SCA, PLAB and Ortho. **CASC is excluded**,
  as in the legacy constants.
- Attribution runs for 90 days and only forwards: somebody who followed a
  partner link *after* signing up was not sent by that partner.
- An acquisition is written **once**. Re-attributing a user because they later
  clicked another partner's link is how the numbers stop reconciling.
- Reporting access is checked against the partner in the path, not just "is a
  reporter" — otherwise one partner's reporter reads another's numbers.
- Conversion is a share of the stage before, which is the only reading that
  shows where people are lost.
- You cannot refer yourself.
- A referral code works as it did in b2c: reusable, by anybody but its owner, as
  often as they buy. It is typed at checkout, where it swaps the plan for its
  10%-off twin (see `billing`), and its owner is credited only when that payment
  arrives: £2.50 for a one-month plan, £5 for anything longer. Each such purchase
  is its own redeemed row, coded `<CODE>-<suffix>`, which the payout queue lists.
- **The ledger is what a partner is paid on; Mixpanel only corroborates it.**
  Mixpanel switched off, unconfigured, or failing is a `status` on the
  reconciliation report (`mixpanel_unconfigured`, `mixpanel_error`), never a
  refusal. Mixpanel is reached through `core.ports.EventCounts`
  (`mixpanel.py` is the adapter; `MIXPANEL_API_SECRET` and
  `MIXPANEL_QUERY_API_ENABLED` turn it on).
- Spend is an **estimate**: every raw arrival is taken as a paid click at the
  pilot's `cost_per_click_pence` (b2c's default, 40p). The partner invoices on
  its own click records, and the report carries b2c's disclaimer saying so.
- A spend alert fires **once per threshold** until reset, for the highest new
  threshold reached, judged on the whole pilot so far (from the first arrival)
  by the daily job — not on whichever range an admin happened to view, which is
  where b2c ran it.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/growth/arrivals` | none | there is nobody to authenticate yet |
| GET | `/api/v1/growth/partners/{partner}/funnel` | reporter for that partner | `not_a_partner_reporter` (403) |
| GET | `/api/v1/growth/partners/{partner}/ref-ids` | reporter for that partner | the references to put in their links, one per pilot exam |
| POST | `/api/v1/growth/partners/{partner}/reporters` | platform admin | |
| POST | `/api/v1/me/referral-code` | bearer | idempotent |
| GET | `/api/v1/me/referrals` | bearer | |
| GET | `/api/v1/growth/partners/{partner}/reconciliation` | platform admin | `from_date`, `to_date` (inclusive UTC), optional `exam_code`, `utm_campaign`; `invalid_date_range` (422) |
| GET | `/api/v1/growth/partners/{partner}/spend` | platform admin | `from_date`, `to_date`; a read, never sends an alert |
| GET | `/api/v1/growth/partners/{partner}/pilot-config` | platform admin | b2c's defaults until first saved |
| PATCH | `/api/v1/growth/partners/{partner}/pilot-config` | platform admin | `reset_spend_alerts` forgets which thresholds have alerted |

## Jobs
- `check_partner_spend` (daily, 06:15 UTC): queues a `partner_spend_alert` email
  to the pilot's recipients (or `SUPPORT_EMAIL`) for any partner whose estimated
  spend crossed a new threshold, and records it in the same transaction.

## Cross-slice dependencies
`billing` supplies the purchase count for a funnel and the revenue for a spend
report (`revenue_for_users`); `notifications` queues the spend alert.
