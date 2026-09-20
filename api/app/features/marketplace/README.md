# marketplace

## Purpose
Peers offering each other practice slots. Someone posts a time they are free,
someone else claims it, and both join a room at the appointed hour.

## Use cases
- As a **consumer**, I offer a time I am free to practise.
- As a **consumer**, I claim someone else's slot.
- As a **consumer**, I withdraw a slot I offered.
- As **either party**, I join the session shortly before it starts.

## Aggregates & invariants
**AvailabilityPost** is the root; claiming one creates a **PeerSession**.

- **A slot is claimed once.** The row is locked with `SELECT … FOR UPDATE`
  before it is examined, so two people pressing the button at the same moment
  serialise: the second waits, reads the status the first wrote, and is told the
  slot is gone. Checking without the lock means both see `available` and both
  believe they won. b2c does this with a Firestore transaction; this is the same
  guarantee in Postgres, and a test proves it with two real connections.
- You cannot claim your own slot.
- A slot you cannot see is a slot you cannot claim: holding the id of one
  offered inside an institution answers 404, not 403.
- **Everything here is addressed to a room** — see `app/core/audience.py`.
  A post, a slot or a queue place is `public`, addressed to one
  `organisation`, or addressed to one `group`. It was addressed to an exam and
  nothing else, so an institution's trainees had no way to talk among
  themselves and a teaching group had no way to practise together. The audience
  is **opaque**: this slice stores a group id and never learns what a group is,
  which is what lets a teaching cohort, a circuit's candidates and a study
  group somebody forms be the same mechanism without reaching up into `roster`
  or `sittings`. A CHECK constraint refuses a row that names a visibility and
  then nobody, because that reads as public to the filter.

- A slot whose start time has passed cannot be claimed. **Not in the legacy
  check** — claiming a session that already started books nobody into anything.
- Only the person who offered a slot may withdraw it, and only before it completes.
- A session opens ten minutes before its start time. Joining an hour early
  leaves someone alone in a room wondering whether it is broken.
- A stranger asking about a session gets 404, not 403: a session id is not
  something they should be able to confirm exists.
- `post_unavailable` is 409 rather than 404 — the caller saw a real slot, and
  "someone claimed it" is different news from "it never existed".

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET/POST | `/api/v1/marketplace/slots` | bearer | available + claimed feed (B2C parity), cursor-paginated |
| POST | `/api/v1/marketplace/slots/{id}/claim` | bearer | `post_unavailable` (409) |
| DELETE | `/api/v1/marketplace/slots/{id}` | owner | |
| GET | `/api/v1/me/peer-sessions` | bearer | |
| POST | `/api/v1/me/peer-sessions/{id}/join` | participant | creates/links `practice_session_id`; `peer_session_not_open` (409) |
| POST | `/api/v1/me/peer-sessions/{id}/cancel` | participant | |

## Jobs
A reminder before each session is not yet ported; b2c sends one.

## Cross-slice dependencies
Calls `catalog` to resolve an exam. Peer sessions are referenced by `attempts`
via `peer_session_id` for the `peer` attempt kind.
