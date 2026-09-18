# One attempt, traced end to end

The single flow that crosses every boundary in the system: browser, API, the marking
engine, LiveKit, the voice worker and the job queue. Follow this once and the rest of
the codebase has a shape.

Most of the notes below are a legacy failure that is deliberately not being repeated.

Published version: https://claude.ai/artifact/DdGp1umMckFMvBiiMaLPWQ

## Phase 1 — the candidate starts (browser → platform-api)

**1. `POST /api/v1/attempts` → `attempts.service.start_attempt`**

Resolves the exam code to a row, then applies the entitlement gate. *The gate lives
here, not in each caller*, so every route that can start a session — practice, a set
entry, a slot dispatch, a peer session — passes through the same check, with
free-trial state resolved alongside it.

> writes: `attempts`, status `created`, no definition yet

**2. `POST /api/v1/attempts/{id}/voice-token` → `voice.service.grant_for_attempt`**

Refuses an attempt that is not yours, or one already at `interaction_complete`,
`evaluated` or `failed`. Maps the attempt kind to a session type and then to a worker
**family** — with no default, deliberately: *defaulting here would undo the guarantee
that a patient simulation is never dispatched to the help worker.*

If the configured mode is Cloud, capacity is checked by `slots_free`, which *reserves
the slot as it answers*, because asking and then taking would race. Past the cap it
falls back to our own workers rather than refusing.

The token carries exactly three metadata strings — `attempt_id`, `backend`,
`candidate_ref` — which is what stops the dispatch payload becoming a second, drifting
copy of the attempt.

> writes: a Redis cloud-slot reservation, when routing Cloud

## Phase 2 — the worker joins (LiveKit → worker → platform-api)

**3.** The worker joins the room and reads the `backend` label from the token
metadata, looking this API up by that label in its own `VOICE_BACKENDS_JSON`. That is
how platform-api, b2b and b2c can all be live at once under different labels during
the cutover.

**4. `GET /api/worker/attempts/{id}` with `X-Worker-Secret` → `bootstrap`**

On the first bootstrap the definition is rendered here: the runnable station version
and exam are loaded and handed to the engine's renderer. *It is frozen only if the
render was real.* A degraded render — a station whose scenario will not render — is
still served so the session is never blocked, but not persisted, so the next bootstrap
tries again and the attempt gets the real thing once the station is fixed.

Both legacy backends freeze unconditionally, which is why an unresolved station there
pins a generic patient prompt to the attempt forever, and every replay shows the same.

> writes: `attempts.definition` + `definition_frozen_at`, on a real render only

**5.** The same call moves the attempt `created → running`.

*A worker fetching the bootstrap is the session beginning* — it is the only start
signal that exists, since nothing else reports one. Without it the attempt stays
`created`, the finished transcript cannot move it to `interaction_complete`, and the
marking is never queued: an unmarked attempt with a full transcript behind it.

> writes: `attempts.status`, `started_at`

## Phase 3 — the conversation (worker → platform-api, repeatedly)

**6. `POST /api/worker/attempts/{id}/transcript-chunks`, turn by turn**

Best-effort: the worker never reads the response, so posts repeat. Deduplicated on
`(attempt_id, message_id)` rather than trusted to arrive once.

> writes: `transcript_messages`

## Phase 4 — the session ends (worker → platform-api → job queue)

**7. `POST /api/worker/attempts/{id}/transcript` → `accept_transcript`**

*The final transcript is the authority.* Chunks are best-effort and may have been
dropped, so anything missing is filled in from this payload rather than assumed to
have arrived.

> writes: `transcripts.complete`, `attempts.status = interaction_complete`

**8. `enqueue_scoring`, inside the same transaction**

Deliberately *not* procrastinate's `defer_async`: its connector holds its own pool, so
deferring through it commits the job on a different connection and the job could land
while the transcript that justified it rolls back. Calling procrastinate's SQL
function on our own session keeps it to one transaction — the work and the fact that
it is owed are recorded together, so either both land or neither.

The queueing lock `score:{attempt}:{policy}` makes a redelivered transcript idempotent.

> writes: a procrastinate job row, in the request transaction

## Phase 5 — marking (job worker → the engine)

**9.** `score_attempt` picks the policy off the **frozen definition**, so re-marking a
past attempt uses the framework it was actually run against rather than whatever the
station says today. If there is no frozen definition — a transcript arrived for an
attempt the worker never bootstrapped — it falls back to the exam's own framework with
a warning, because *the alternative was a log line and a transcript nobody would ever
score*, which is what happened.

**10.** Three guards before the engine is called:

- Already scored under this policy → nothing written; the queue may deliver twice.
- Status not markable → skip; a job can arrive before the status settles, or after a
  later failure.
- Empty transcript → the attempt is **failed** with reason `empty_transcript`.

If the evaluator itself raises, the attempt is left at `interaction_complete` so a
retry can still mark it — failing it there would discard a transcript we still hold.

**11.** The engine's payload is stored and the attempt moves to `evaluated`. Unique on
`(attempt_id, policy_version)`, so a second run under the same policy writes nothing
and a run under a different one sits beside the first. Re-marking never moves an
already-evaluated attempt's status.

> writes: `assessment_results`, `attempts.status = evaluated`

## Phase 6 — reading it back

**12. `GET /api/v1/attempts/{id}/result` and `/transcript`**

Visible to the attempt's owner and to platform admins. An institution's formal
decision is a different path entirely — `candidate_result_revisions`, signed off and
released — and a candidate sees that only through `GET /me/results/{sitting_id}`, only
once released.

## Variant — when it is an examination

Steps 1–2 are replaced by the circuit's own clock (ADR 0018). Nobody asks for a
token per station and nobody presses "send the patient in".

The candidate joins the circuit's room once, at the start, with
`POST /me/circuits/{id}/join-token` — a token with **no agent attached**, because
the circuit brings the patient rather than the candidate's token carrying one.
Attaching one here put a second patient in the room beside the first, and both
answered as the patient.

When the reading period ends, the transition scheduled for that moment fires and
the consultation begins: the attempt is created and the agent is dispatched into
the room, in one transaction. *Each dispatch creates a new attempt* — which is
what the partial unique index enforces: a slot may have at most one attempt that
has not failed, so sending the patient again fails the previous one rather than
overwriting its recording.

When the consultation's own deadline passes, the next transition removes the
agent. **That is how the recording ends.** The worker has no timer — it ends on
the candidate leaving, the room closing, or being removed — and on its way out it
posts the full transcript, which queues the marking. So the bell ringing and the
recording being delivered are the same act.

Two overrides create a second attempt: `resend-patient`, when the patient did not
arrive, and `redo-station`, when the station has to be given back. Both fail the
live attempt rather than deleting it, so what happened the first time survives
beside the retry.

From step 3 onward the flow is identical.
