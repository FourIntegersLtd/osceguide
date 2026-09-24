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
- **A recording is best-effort; a consultation is not.** An egress that cannot
  be started, or a bucket that is not configured, is logged and the session
  carries on. Two people practising is the thing being protected; feedback
  built from it afterwards is not worth ending a consultation for.
- **Only the doctor is marked.** The rubric is written for the doctor's
  performance, and the patient is playing a part. The patient is never given
  the doctor's attempt id, which is why `session_read` withholds it rather than
  the client choosing not to show it.
- A peer session becomes **one attempt**, `kind='peer'`, pointing back at the
  session through `attempts.peer_session_id`. From there it is marked by the
  same engine, against the same frozen rubric, as a mock — there is no second
  scoring path to keep in step.

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
| POST | `/api/v1/me/practice-sessions/{id}/voice-token` | bearer | Join the room the pair were matched into; `practice_session_ended` (409) |

There is deliberately no `start-egress`, `transcribe` or `feedback-status`
route. The retiring client needed all three because its browser drove the
recording; here the phase machine on the server already knows when the
consultation starts and stops, and the feedback is read back through the
attempt the session names — `GET /api/v1/attempts/{id}/result` and
`/stream` — rather than through a second set of routes that would have to be
kept in step with them.

## Jobs
| Task | Queue | When |
|---|---|---|
| `try_match_practice_room` | `matching` | somebody joins the queue, in the same transaction as the queue row |
| `match_practice_queue` | `matching` | every minute; drains every room as a safety net |
| `expire_practice_queue` | `matching` | marks waiting entries past ten minutes as `expired` |
| `transcribe_peer_session` | `transcription` | the consultation phase ends, in the same transaction as the stopped recording |

`transcribe_peer_session` waits for the recording to land in S3 — egress upload
lags the stop by seconds — and reschedules itself rather than sleeping in the
worker, giving up after twenty looks and recording why on the session. It then
transcribes, recovers the doctor's and the patient's turns from the one mixed
track, and hands the transcript to `attempts.service_offline`, which freezes
the rubric, stores the turns and queues the marking.

The procrastinate worker must be running for matching, expiry and
transcription.

## Cross-slice dependencies
Calls `catalog` to resolve an exam, `voice.service_recording` for the room
recorder, `media_production.service_storage` for the object store, and
`attempts.service_offline` to turn a finished transcript into a marked attempt.
Each of those is a named function on a service, which is the only door a slice
offers another.
