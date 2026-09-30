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
- **The transcript and the marking have two readers, not one.** The candidate who
  spoke them, and the supervisor named on the circuit they were spoken in —
  `service_access.ensure_readable`. Being named *is* the permission, as being
  rostered on is the permission to join the room; a supervisor of another
  circuit, an administrator who was not named, and a platform job that brings no
  memberships are all refused, as they were before. Nothing else this slice serves
  was widened: the brief, the model answer, the attempt row and the stream still
  answer to their owner alone. Who a circuit names comes from
  `sittings.service_reads.supervisor_for_slot`.
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
| GET | `/api/v1/attempts/{id}/transcript` | owner, platform admin, or the named examiner | `attempt_not_yours` (403) for every other supervisor, and for an org admin not named on the circuit |
| GET | `/api/v1/attempts/{id}/result` | owner, platform admin, or the named examiner | the same pair of reads, widened together |
| GET | `/api/v1/attempts/{id}/brief` | owner or org admin | The candidate's reading-time brief. Readable from `created`: the attempt exists before the reading period does |
| GET | `/api/v1/attempts/{id}/review` | owner or org admin | The model answer — the patient's ideas and concerns, and the management plan. `attempt_not_finished` (409) until the interaction is over |
| GET | `/api/v1/attempts/{id}/roleplay` | owner | Post-consultation patient script for practising as the patient; explicit field allowlist |
| POST | `/api/v1/attempts/{id}/debriefs` | owner | Recorded, finished library/self-practice consultation only; mock entries use the station-set route and its counters |
| GET | `/api/v1/attempts/{id}/coverage` | owner | Persisted live coverage, separate from final marks; unsupported for exam slots, peer sessions and debriefs |
| GET | `/api/v1/me/attempts` | bearer | This person's attempts, newest first. `station_version_id` and `set_entry_id` narrow it |
| GET | `/api/v1/attempts/{id}/stream` | stream ticket | The attempt, pushed until it is marked. Replaces b2c's feedback-status stream and the two pollers behind it |
| GET | `/api/v1/platform/users/{id}/attempts` | platform admin | One person's attempts with their marking state: transcript delivered, results, the newest scoring job. `?status=` narrows |
| GET | `/api/v1/platform/attempts/{id}` | platform admin | The support detail: frozen definition present, turns received, every scoring job ever queued |

The console's per-station view of a person's attempts, and the one delete this
table has (`service_platform.py`), are routed from `station_sets`,
which owns the counter beside them.
| GET | `/api/worker/attempts/{id}` | worker secret | `{attempt, scenario}`, no evaluation policy |
| POST | `/api/worker/attempts/{id}/transcript-chunks` | worker secret | idempotent |
| POST | `/api/worker/attempts/{id}/transcript` | worker secret | exactly once; enqueues scoring |
| POST | `/api/v1/{platform,orgs/{org_slug}}/rubrics/{id}/versions/{n}/trial` | platform admin / org admin | trial mark (below) |

**Trial mark** (`service_trial.py`, `router_trial.py`, rubric plan §8). A rubric
version of the caller's own, a draft included, marked by the real engine
against `{transcript}` (pasted, `Speaker: text` lines; `Doctor`/`Dr`/`Candidate`
... are the candidate) or `{attempt_id}` (one of the caller's own attempts).
Everything refusable is refused before the stream opens (422
`invalid_rubric`/`invalid_trial_transcript`, 404, 429, 503
`marker_unavailable`). The stream is `connected`, a `snapshot` (`TrialMarkRead`)
every 5 s while `marking`, then one `marked` (marks + totals) or `failed`
snapshot. A `POST`, so browsers read it with `fetch`. It stores nothing.

## Jobs
`score_attempt` — runs the engine evaluator against a completed transcript and
stores one `assessment_results` row. Idempotent on `(attempt_id, policy_version)`.

`update_attempt_coverage` on queue `coverage` processes candidate turns against
the frozen rubric using the engine's grounded, monotonic live detector. Work is
coalesced and serialized per attempt, and stored in `attempt_live_coverage`.
It never changes final assessment results. Deploy migration `h9i0j1k2l3m4` and
run a background worker consuming `coverage`, `scoring` and `summaries` for the
complete practice flow; a connected LiveKit worker alone cannot mark or summarize.

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
The persona, opening line and expanded history are excluded from both reads.
The separate owner-only `roleplay` read releases an allowlisted patient script
after the consultation for patient-role practice. Examiner context is never
released by any of these reads.

This is why `stations.LibraryStationRead` carries no `content`: browsing the
library is open to every signed-in user, while these reads are owner-only and
are reached only through an attempt, which the entitlement gate has already
allowed.
