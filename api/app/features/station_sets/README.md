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
- As a **consumer**, I talk an attempt through afterwards, against a separate limit.
- As a **consumer**, I debrief a station I have already run.
- As a **consumer**, I rename a set, and throw away one I have not started.
- As a **consumer**, I edit a set's stations — the legacy "edit session" screen —
  keeping, dropping and adding stations in one call.
- As a **consumer** whose access lapsed, my sets are still there when I renew.

## Aggregates & invariants
**StationSet** owns its entries.

- The per-station attempt limit comes from the exam, and a limit of zero means
  unlimited.
- A debrief needs a completed attempt: there is nothing to talk about otherwise.
  Debriefs count against their own limit.
- A locked set refuses new attempts and is never deleted **by the platform**:
  locking is what happens to somebody's work when their access lapses, and it
  is not a reason to destroy it. The owner may still throw a locked set away,
  because that is them choosing to.
- **A set is deletable; a recording is not.** An entry is what a set attempt
  points at, and the schema refuses to take an entry out from under a recording
  (`RESTRICT`, and the CHECK that a set attempt must name its entry). So the
  delete asks `attempts` — never its own counters, which the console zeroes
  while keeping the recording — and refuses with `set_has_attempts` rather than
  deleting the consultation, its transcript and its marking to get an answer.
  The retiring client deleted the session and its progress rows and left the
  transcripts behind; the orphan is what this refuses, and the erasure is what
  the console's audited `delete-progress` route is for.
- A set is complete when every entry has been attempted; an empty set is not
  complete, or one created and never populated would report itself finished.
- Counters are incremented in SQL inside the attempt's transaction, not read then
  written. b2c mutates an array on the user document with no transaction, so two
  sessions finishing together lose a count and a limit can be exceeded.
- **Editing a set's stations keeps, drops and adds, not replace-and-lose-progress.**
  A version that stays in the new list keeps its existing entry, counters and
  all — a station left in place must not look, to the candidate, like one they
  have never sat. A version dropped is only actually removed if nothing has
  been attempted at it yet; one that has is left in place and reported as
  `set_entry_has_attempts`, the same shape as a whole set that cannot be deleted.
  Matching a requested version against an existing entry is by position among
  equal version ids, so asking for the same station twice keeps both of its
  entries rather than treating the second as new.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET/POST | `/api/v1/me/station-sets` | bearer | each set carries its own progress |
| GET | `/api/v1/me/station-sets/{id}` | owner | `set_not_found` (404) |
| PATCH | `/api/v1/me/station-sets/{id}` | owner | rename, and/or — the legacy "edit session" screen — replace its stations via `station_version_ids` (keeps entries for versions that stay, drops those with no attempts, adds the rest). `set_not_found` (404), blank name rejected, `set_locked` (409), `station_version_not_usable` (409), `set_entry_has_attempts` (409) |
| DELETE | `/api/v1/me/station-sets/{id}` | owner | throw a set away with its entries. `set_not_found` (404); `set_has_attempts` (409) while a recording of a consultation still points at one of them |
| POST | `/api/v1/me/station-sets/{id}/entries/{entry_id}/attempts` | owner | `attempt_limit_reached` (409), `set_locked` (409) |
| POST | `/api/v1/me/station-sets/{id}/entries/{entry_id}/debriefs` | owner | Talk through an attempt already made; `nothing_to_debrief` (409), `attempt_limit_reached` (409) |
| GET | `/api/v1/platform/users/{id}/stations` | platform admin | one row per station the person has sat: attempts that exist, how many were marked, the newest, and the counters on their set entries; `user_not_found` (404) |
| POST | `/api/v1/platform/users/{id}/stations/{station_id}/reset-attempts` | platform admin | zero the entry counters for that station — the old console's "reset attempts"; attempts and marking kept; audited `user.station_attempts_reset`; `station_not_found` (404) |
| POST | `/api/v1/platform/users/{id}/stations/{station_id}/delete-progress` | platform admin | `{reason}`; delete every attempt at the station (turns, transcript, results and debrief summary cascade) and take it out of their sets; audited `user.station_progress_deleted`; `attempt_in_progress` (409) while one is running |

## Jobs
None. Locking on expiry belongs with `entitlements` and is not yet wired.

## Cross-slice dependencies
Calls `catalog` for the exam and its attempt limit, and `attempts` to create the
attempt — which applies the entitlement check. Deleting a set asks `attempts`
which of its entries a recording still points at, because that is the fact that
decides whether the delete may happen; the entry's own counter is not it, since
the console zeroes the counter and keeps the recording.

The console routes (`service_platform.py`) also read `stations` for a
station's title and versions, ask `attempts` to delete a person's attempts at
those versions, and write the audit row through `tenancy.service_audit`. They
live here rather than in `attempts` because the counter the old console reset
is this slice's entry.
