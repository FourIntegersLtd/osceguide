# station_sets

## Purpose
A learner's own collection of stations to practise — what b2c calls a mock.

Deliberately not a circuit. A set is personal and re-attemptable: its entries
carry attempt counters, and the whole thing locks when access lapses rather than
being deleted, so the work reappears on renewal. A circuit slot is one-shot and
scheduled by somebody else. Collapsing them would give a slot an attempt counter
and a lock flag, which is the b2b shape in reverse.

Both produce rows in the one `attempts` table.

## Use cases
- As a **consumer**, I build a set from the station library and work through it.
- As a **consumer**, I re-attempt a station until I have used my attempts.
- As a **consumer**, I debrief a station I have already run.
- As a **consumer** whose access lapsed, my sets are still there when I renew.

## Aggregates & invariants
**StationSet** owns its entries.

- The per-station attempt limit comes from the exam, and a limit of zero means
  unlimited.
- A debrief needs a completed attempt: there is nothing to talk about otherwise.
  Debriefs count against their own limit.
- A locked set refuses new attempts and is never deleted.
- A set is complete when every entry has been attempted; an empty set is not
  complete, or one created and never populated would report itself finished.
- Counters are incremented in SQL inside the attempt's transaction, not read then
  written. b2c mutates an array on the user document with no transaction, so two
  sessions finishing together lose a count and a limit can be exceeded.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET/POST | `/api/v1/me/station-sets` | bearer | each set carries its own progress |
| GET | `/api/v1/me/station-sets/{id}` | owner | `set_not_found` (404) |
| POST | `/api/v1/me/station-sets/{id}/entries/{entry_id}/attempts` | owner | `attempt_limit_reached` (409), `set_locked` (409) |

## Jobs
None. Locking on expiry belongs with `entitlements` and is not yet wired.

## Cross-slice dependencies
Calls `catalog` for the exam and its attempt limit, and `attempts` to create the
attempt — which applies the entitlement check.
