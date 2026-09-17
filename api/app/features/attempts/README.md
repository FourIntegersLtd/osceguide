# attempts

## Purpose
One candidate running one scenario, however they came to be doing it. This is
the shared core: consumer practice, a mock-set station, a debrief, institutional
self-practice, an exam slot and a peer session all write rows in one table,
because they are the same event with different reasons for being permitted.

Also owns the worker contract — the routes the LiveKit assessment worker calls —
and the job that scores a delivered transcript.

## Use cases
- As a **consumer**, I start an attempt at a station and read my feedback afterwards.
- As a **trainee**, I run my assigned slot; a re-dispatch gives me a fresh attempt
  and does not destroy the first recording.
- As **anyone**, I run a debrief about an earlier attempt of mine.
- As the **LiveKit worker**, I fetch the frozen attempt I was handed, stream the
  turns as they happen, and deliver one completed transcript.
- As the **platform**, I score a delivered transcript and store the result immutably.

## Aggregates & invariants
**Attempt** is the root; its turns, transcript and results live inside it.

- `id` is its own identity. b2c made it the room name, b2b made it the slot id;
  both leaked into the worker contract, and b2b's meant a re-dispatch overwrote
  the only transcript column the slot had.
- The definition freezes once, on the **first successful render**. A degraded
  render is served so the session can proceed and is not recorded — both legacy
  backends freeze unconditionally, which pins a generic prompt to an attempt
  permanently.
- Freezing is guarded in the UPDATE (`WHERE definition IS NULL`), so two workers
  racing to bootstrap cannot both believe they were first.
- `created → running → interaction_complete → evaluated`, plus `→ failed` from
  any non-terminal state. Nothing returns from `evaluated`.
- Exactly one optional reference matches the kind — a CHECK, because six paths
  create attempts and only one needs to be wrong.
- A slot has at most one attempt that has not failed: a partial unique index.
- Chunks are idempotent on `(attempt_id, message_id)`; the completed transcript
  is accepted once; scoring is idempotent per `policy_version`.
- The bootstrap payload **never** contains `evaluation_policy`. Marking is the
  backend's business and the worker cannot import an evaluator.

## Routes
| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/attempts` | bearer | kind-specific body; checks entitlement |
| POST | `/api/v1/attempts/{id}/abandon` | owner | `invalid_attempt_state` (409) once the interaction is complete |
| GET | `/api/v1/attempts/{id}` | owner or org admin | |
| GET | `/api/v1/attempts/{id}/transcript` | owner or org admin | |
| GET | `/api/v1/attempts/{id}/result` | owner or org admin | |
| GET | `/api/worker/attempts/{id}` | worker secret | `{attempt, scenario}`, no evaluation policy |
| POST | `/api/worker/attempts/{id}/transcript-chunks` | worker secret | idempotent |
| POST | `/api/worker/attempts/{id}/transcript` | worker secret | exactly once; enqueues scoring |

## Jobs
`score_attempt` — runs the engine evaluator against a completed transcript and
stores one `assessment_results` row. Idempotent on `(attempt_id, policy_version)`.

## Cross-slice dependencies
Calls `catalog` to resolve an exam, `stations` to resolve a scenario, and
`entitlements` to decide whether an attempt may start.
