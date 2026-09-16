# dashboard

## Purpose
One call for the learner's home screen. A read model over `entitlements`,
`attempts` and `station_sets`.

The SCA dashboard currently makes seven requests — four RAG endpoints, a weekly
trend and two marketplace lists — and joins them in the browser. The B2B org
dashboard makes five, four of which exist only to produce a count.

## Use cases
- As a **consumer**, I open the app and see my access, my progress and where I
  left off, in one request.

## Aggregates & invariants
None, deliberately. This slice owns no tables and has no `domain.py`: a
dashboard is a projection, not a thing anyone owns, and no rule is enforced
about one. It reads through other slices' services rather than their tables, so
it cannot quietly become a second owner of anyone's data.

Screens change often and the domain should not follow them, which is why this
exists as its own slice rather than as fields grafted onto `attempts`.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/me/dashboard` | bearer | entitlements, per-exam progress, recent attempts, sets |

## Jobs
None. Anything expensive enough to need caching belongs behind Redis here rather
than in the callers.

## Cross-slice dependencies
Reads `entitlements`, `attempts` and `station_sets` through their services. Sits
at the top of the layer order and nothing depends on it.
