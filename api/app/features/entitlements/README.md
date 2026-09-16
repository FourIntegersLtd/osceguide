# entitlements

## Purpose
Whether someone may attempt an exam, and why. One predicate with several
sources, separate from whatever payment or membership caused it.

Replaces four unrelated answers: `has_paid` plus `plan_end_date` on a Firestore
user document (of which a person had four, one per product), b2b's
`b2b_practice_entitlements`, an SSO tenant's plan end date, and a free-trial rule
recomputed on every request and stored nowhere.

## Use cases
- As a **consumer**, my purchase grants me access until it expires.
- As a **trainee**, my institution grants me access to the exams it runs.
- As a **new consumer**, I practise a few stations before deciding to buy.
- As an **org admin**, I grant and revoke access for a member.
- As the **platform**, I refuse to start an attempt nobody is entitled to.

## Aggregates & invariants
**Entitlement** stands alone; it references a user, an exam and its source.

- A payment does not *mean* access; it *grants* it. Revoking after a refund
  leaves the payment record intact.
- Revocation sets `revoked_at` rather than deleting, so "why could they do
  that?" is answerable after the fact.
- A grant counts only when started, unexpired and unrevoked. One live grant is
  enough; sources do not stack or conflict.
- The free trial is consulted only when nothing is granted, and its rule is
  ported verbatim: three set stations **or** three completed attempts **or** an
  account older than fourteen days ends it, each counted separately rather than
  summed, with a strict age comparison. Changing any of that changes somebody's
  access today.
- One error code whatever the reason; the distinction between "expired" and
  "never had one" goes in `details`, because the client shows the same prompt.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/me/entitlements` | bearer | including expired, with `live` computed |
| POST | `/api/v1/orgs/{org_slug}/entitlements` | org admin | grants to a member |

## Jobs
None. `billing` writes entitlements through this slice's service.

## Cross-slice dependencies
Calls `catalog` to resolve an exam. `attempts` calls `require()` before creating
anything; nothing else reads a paid flag.
