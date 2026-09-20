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
| GET | `/api/v1/attempts/{id}/brief` | owner or org admin | The candidate's reading-time brief. Readable from `created`: the attempt exists before the reading period does |
| GET | `/api/v1/attempts/{id}/review` | owner or org admin | The model answer — the patient's ideas and concerns, and the management plan. `attempt_not_finished` (409) until the interaction is over |
| GET | `/api/v1/me/attempts` | bearer | This person's attempts, newest first. `station_version_id` and `set_entry_id` narrow it |
| GET | `/api/v1/attempts/{id}/stream` | stream ticket | The attempt, pushed until it is marked. Replaces b2c's feedback-status stream and the two pollers behind it |
| GET | `/api/v1/platform/users/{id}/attempts` | platform admin | One person's attempts with their marking state: transcript delivered, results, the newest scoring job. `?status=` narrows |
| GET | `/api/v1/platform/attempts/{id}` | platform admin | The support detail: frozen definition present, turns received, every scoring job ever queued |

The console's per-station view of a person's attempts, and the one delete this
table has (`service_platform_progress.py`), are routed from `station_sets`,
which owns the counter beside them.
| GET | `/api/worker/attempts/{id}` | worker secret | `{attempt, scenario}`, no evaluation policy |
| POST | `/api/worker/attempts/{id}/transcript-chunks` | worker secret | idempotent |
| POST | `/api/worker/attempts/{id}/transcript` | worker secret | exactly once; enqueues scoring |

## Jobs
`score_attempt` — runs the engine evaluator against a completed transcript and
stores one `assessment_results` row. Idempotent on `(attempt_id, policy_version)`.

## Cross-slice dependencies
Calls `catalog` to resolve an exam, `stations` to resolve a scenario and to read
back the document behind one, and `entitlements` to decide whether an attempt
may start. The platform console's reads ask `health.service_jobs` what the
queue holds for an attempt and `identity` whether the account exists.

## What a candidate may read of a station
`station_versions.content` is one document holding both the brief and the
answers, so `service_material` splits it rather than passing it through:
`doctor_information` and the flat candidate keys before the consultation, the
management plan and the patient's ideas, concerns and expectations after it.
How the patient is played — the persona, the opening line, the expanded history
— never leaves the server at all, and neither does the examiner's context.

This is why `stations.LibraryStationRead` carries no `content`: browsing the
library is open to every signed-in user, while these reads are owner-only and
are reached only through an attempt, which the entitlement gate has already
allowed.
