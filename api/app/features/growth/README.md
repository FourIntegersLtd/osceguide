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

## Aggregates & invariants
**PartnerArrival**, **Acquisition**, **PartnerReporter** and **Referral**.

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

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/growth/arrivals` | none | there is nobody to authenticate yet |
| GET | `/api/v1/growth/partners/{partner}/funnel` | reporter for that partner | `not_a_partner_reporter` (403) |
| GET | `/api/v1/growth/partners/{partner}/ref-ids` | reporter for that partner | the references to put in their links, one per pilot exam |
| POST | `/api/v1/growth/partners/{partner}/reporters` | platform admin | |
| POST | `/api/v1/me/referral-code` | bearer | idempotent |
| GET | `/api/v1/me/referrals` | bearer | |

## Jobs
None. Mixpanel reconciliation and spend alerts are not ported — see
`platform-web/docs/BACKLOG.md` G-1.

## Cross-slice dependencies
None outward. `billing` supplies the purchase count for a funnel; wiring that is
G-2.
