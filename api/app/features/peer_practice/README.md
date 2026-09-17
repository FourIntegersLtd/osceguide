# peer_practice

## Purpose
Pairing two people who want to practise together, one playing the doctor and one
the patient.

## Use cases
- As a **consumer**, I join a queue and am told where I stand.
- As a **consumer**, I am matched with someone and given a room.
- As a **consumer**, I leave the queue, or end a session.
- As the **platform**, I pair whoever is waiting, fairly.

## Aggregates & invariants
**QueueEntry**, **PracticeSession** and **PracticeHistory** are separate roots.

- One live place in the queue per person per exam — a partial unique index.
  Joining twice returns the place you already hold rather than a second one;
  it is somebody tapping a button again, not an error worth refusing. That
  holds **across rooms**: asking to wait in your institution's queue while
  already waiting in the public one returns the place you have, rather than
  putting you in two queues at once.
- **Matching is per room, and so is the queue position.** Pairing an exam as a
  single pool would put a trainee waiting inside their institution with a
  stranger. Somebody in a private queue was also told how many people were
  ahead of them in the public one, none of whom they could ever be matched with.
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

- Matching claims queue rows with `FOR UPDATE SKIP LOCKED`, so two matchers
  running at once pair different people rather than both pairing the same two.
- **Role assignment is ported exactly**, because the rules are about fairness:
  someone who must never be doctor is always patient; otherwise each takes the
  opposite of last time; a newcomer takes the doctor's part, which is the one
  worth practising; and failing that, the less experienced person gets it.
- Where b2c picks at **random** between two equals, this picks by user id, so a
  failing match is reproducible. The fairness argument is already satisfied by
  the rules above it.
- A pair that cannot be formed — two people who must both be patient — is
  skipped rather than left blocking the queue behind them.
- The role is recorded when the pair is made, not when the session ends, so
  somebody who abandons a session still does not get the same part twice.
- `never_doctor` is a column. b2c hardcodes three personal email addresses into
  the matcher; it is a property of a person, so it lives on the person.
- A stranger asking about a session gets 404, not 403.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/peer-practice/queue` | bearer | idempotent |
| GET | `/api/v1/peer-practice/queue/{id}` | owner | position, waiting count and session in one call |
| GET | `/api/v1/peer-practice/queue/{id}/stream` | owner (bearer or `?ticket=`) | the same payload pushed (SSE); closes as soon as the answer stops being `waiting` |
| DELETE | `/api/v1/peer-practice/queue/{id}` | owner | |
| GET | `/api/v1/me/practice-sessions` | bearer | |
| GET | `/api/v1/me/practice-sessions/{id}` | participant | |
| POST | `/api/v1/me/practice-sessions/{id}/end` | participant | |

## Jobs
`match_practice_queue` — periodic, every minute. Periodic rather than triggered
on join: two people arriving together would otherwise both try to match, and one
would find an empty queue.

## Cross-slice dependencies
Calls `catalog` to resolve an exam. Recording and transcription of a peer
session are not ported — see `docs/OPEN-QUESTIONS.md` P-1.
