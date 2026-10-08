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
- Attribution has no time limit and only forwards: once a partner's link is
  clicked, that partner is credited however long the signup takes, but somebody who followed a
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
| GET | `/api/v1/growth/partners/{partner}/funnel` | reporter for that partner | `not_a_partner_reporter` (403); optional `from_date`+`to_date` (both, or neither), `exam_code`, `utm_campaign` narrow it — omit all four for the whole pilot to date |
| GET | `/api/v1/growth/partners/{partner}/ref-ids` | reporter for that partner | the references to put in their links, one per pilot exam |
| POST | `/api/v1/growth/partners/{partner}/reporters` | platform admin | |
| POST | `/api/v1/me/referral-code` | bearer | idempotent |
| GET | `/api/v1/me/referrals` | bearer | |
| GET | `/api/v1/growth/partners/{partner}/reconciliation` | platform admin | `from_date`, `to_date` (inclusive UTC), optional `exam_code`, `utm_campaign`; `invalid_date_range` (422) |
| GET | `/api/v1/growth/partners/{partner}/spend` | platform admin | `from_date`, `to_date`; a read, never sends an alert |
| GET | `/api/v1/growth/partners/{partner}/pilot-config` | platform admin | b2c's defaults until first saved |
| PATCH | `/api/v1/growth/partners/{partner}/pilot-config` | platform admin | `reset_spend_alerts` forgets which thresholds have alerted |

### The BMJ dashboard
Ported from b2c's `partner_dashboard_service`, `bmj_metrics_service`,
`bmj_anomaly_service` and `partner_reporting_service`. No migration backs any
of it: every figure is computed on the fly from `PartnerArrival`,
`Acquisition`, `PartnerReporter` and `billing.payments`. All ten read the
`from_date`/`to_date`/`exam_code`/`utm_campaign` filters the funnel does;
the `-over-time` routes also take `bucket` (`day`/`week`/`month`,
`invalid_bucket` (422) otherwise). `exam_code` and `utm_campaign` narrow arrivals *and* sign-ups alike (a sign-up's campaign is its arrival's), as b2c's `original_exam`/`original_campaign` filters do and gap-fill empty buckets with zero so a
chart's x-axis is continuous.

**Admin (platform admin only) — figures include revenue and margin:**

| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/growth/partners/{partner}/summary` | the Overview tab: arrivals, acquisitions, reconciliation, revenue, spend and the anomaly panel in one call |
| GET | `/api/v1/growth/partners/{partner}/revenue` | revenue by plan, standalone |
| GET | `/api/v1/growth/partners/{partner}/revenue-over-time` | chart |
| GET | `/api/v1/growth/partners/{partner}/arrivals` | cursor-paginated, `search` by visitor key |
| GET | `/api/v1/growth/partners/{partner}/acquired-users` | cursor-paginated, each row enriched with its arrival's UTM tags |
| GET | `/api/v1/growth/partners/{partner}/reporters` | active and revoked |
| DELETE | `/api/v1/growth/partners/{partner}/reporters/{email}` | 204; `reporter_not_found` (404) on a second revoke |

**Partner mode (that partner's reporter) — money never appears, by construction:**

| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/growth/partners/{partner}/reporting/summary` | fee-framed, not revenue-framed: `PartnerFeeSummary` carries an estimated spend and nothing else money-shaped, plus breakdown by exam and by campaign (counts only) |
| GET | `/api/v1/growth/partners/{partner}/reporting/visits-over-time` | chart |
| GET | `/api/v1/growth/partners/{partner}/reporting/signups-over-time` | chart |
| GET | `/api/v1/growth/partners/{partner}/reporting/fee-over-time` | visits and their estimated fee per bucket |

Anomalies (`detect_anomalies` in `domain.py`, up to 5, most severe first):
`mixpanel_unavailable` (info), `mixpanel_drift` (warning ≥10%, critical ≥25%),
`funnel_order_violation` (critical), `acquired_count_mismatch` (warning —
structurally unreachable from `read_summary` today, since it passes the same
value for both `signup_count` and `acquired_user_count`; kept general for a
future caller that could pass them independently), `negative_net_margin`
(warning — fires on nearly any range with arrivals and no matching revenue,
since the default 40p/click estimate outruns zero revenue immediately).

## Jobs
- `check_partner_spend` (daily, 06:15 UTC): queues a `partner_spend_alert` email
  to the pilot's recipients (or `SUPPORT_EMAIL`) for any partner whose estimated
  spend crossed a new threshold, and records it in the same transaction.

## Demo data
`scripts/seed_partner_attribution.py` (`--dry-run`, `--clean`) writes 84
synthetic BMJ visitors — arrivals, signups, and 44 payments across all three
plan lengths and all three pilot exams — ported verbatim from b2c's
`_visitor_specs()`. Idempotent by deterministic key (`vk_seed_dashboard_NN`,
`seed_dashboard_u_NN@seed.osceguide.test`, `pi_seed_dashboard_NN`) rather than
a tag column, since neither `growth` nor `billing` has one. Requires `sca`,
`plab` and `ortho` to already exist (`scripts/seed_platform.py` first); flips
their `partner_pilot` flag on if it is not already. Creates `reporter@bmj.com`
with a freshly generated password, printed once on the run that creates the
account.

## Cross-slice dependencies
`billing` supplies the purchase count for a funnel and the revenue for a spend
report (`revenue_for_users`) and the dashboard's revenue breakdown and
over-time chart (`revenue_breakdown_for_users`, `revenue_over_time_for_users`,
`payer_user_ids_among`, which takes the paid-date range: a sign-up is "paid" when that user has a payment inside the range, counted under the exam and campaign of their arrival, as in b2c); `catalog` supplies which exams are in the pilot
(`pilot_exam_codes`); `notifications` queues the spend alert and, on each paid referral purchase, the
`referral_redeemed` email to the referrer (the amount earned, never the buyer's name).

A credit already paid out is not un-paid on a refund or dispute: `claw_back_referral_purchase`
records a second redeemed row with the earnings negated and `clawback_of_id` set (unique, so
once per credit). `earned_pence` totals and the settlement queue then net it off.
