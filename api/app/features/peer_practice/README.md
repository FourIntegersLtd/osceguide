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
  it is somebody tapping a button again, not an error worth refusing.
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
