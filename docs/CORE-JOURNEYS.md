# Core journeys

The journeys a real person must be able to finish. Each is driven in a real
browser by a Playwright spec under `web/e2e/`, against a local platform-api.
Gap IDs refer to `docs/EXPERIENCE-GAPS.md`.

"Local" means it runs with no LiveKit voice. Where a step needs a spoken room,
the journey drives the api seam instead, or the step is listed as skipped with
the reason. The seams used are:

- **circuit start and end** through the api: start works without LiveKit;
  "Next station" returns `503 voice_unavailable`; ending the circuit closes the
  slot as skipped.
- **database seam** (`web/e2e/support/db.ts`): the rows a finished marking
  leaves behind (an evaluated attempt and its `assessment_results`), because
  marking needs a spoken transcript. Only runs after the local-api assertion.
- **microphone**: headless Chrome's `getUserMedia` never resolves, so nothing
  that waits on the mic check can be reached.

## How to run

Prerequisites: docker postgres up, `poetry run alembic upgrade head`,
`poetry run python scripts/seed_platform.py`, and platform-api on `:8002`
(`make start` in `api/`). Then, from `web/`:

```bash
export PATH="$HOME/.nvm/versions/node/v22.22.3/bin:$PATH"
npm run e2e           # everything
npm run e2e:train     # consumer journeys
npm run e2e:assess    # institution journeys
```

Playwright starts its own Next dev server on `:3101` (separate `distDir`,
`.next-e2e`) with `/api/v1` proxied to `http://127.0.0.1:8002`. Set
`E2E_REUSE_SERVER=1` to reuse one that is already running. Global setup refuses
to write anything unless the api host is localhost, then creates a fresh
organisation `e2e-<id>` with an admin, supervisor, trainee, a consumer and a
newcomer, so a run never depends on earlier data. Override with
`E2E_API_URL`, `E2E_WEB_URL`, `E2E_PG_CONTAINER`. Sign-in is rate limited to
10 a minute; the helpers wait and retry on 429 (`loginPatiently` is a test-only workaround for that limit, not product behaviour). Failures keep a trace and
screenshot in `web/test-results/`.

## TRAIN: the consumer

| ID | Journey | Local | Spec |
|---|---|---|---|
| TRAIN-1 | Sign in, reload, sign out | yes | `train/sign-in.spec.ts` |
| TRAIN-2 | Register, choose an exam, reach the first station | yes | `train/first-visit.spec.ts` |
| TRAIN-3 | Create a practice session, reach the pre-start screen | yes, to the pre-start screen | `train/practice-session.spec.ts` |
| TRAIN-4 | Read feedback on a marked station; dashboard moves | yes, marked row seeded | `train/feedback.spec.ts` |
| TRAIN-5 | Update profile, see plans | yes | `train/settings.spec.ts` |
| TRAIN-6 | Speak a practice station and be marked | no, needs LiveKit | skipped |

**TRAIN-1.** Actor: a registered consumer.
1. Open `/login`, enter email and password, submit.
2. Land in the app signed in; reload the page.
3. Still signed in. Sign out; `/app` sends back to `/login`.

Outcome: a reload keeps the session, sign-out ends it (the refresh token is
revoked server-side). Gaps: A-1, A-3, A-6.

**TRAIN-2.** Actor: a brand-new visitor.
1. Open `/register`, create an account.
2. See the exam picker (`users.exam_code` is empty); choose SCA.
3. Reach the first-station prompt. 2b: before an exam is chosen, `/app/me/**`
   shows only the picker.

Outcome: a newcomer cannot reach a page that assumes an exam. Gaps: A-3, A-6.

**TRAIN-3.** Actor: a consumer with an exam.
1. Open practice, "New session"; the session name is generated ("Session 1").
2. Pick a station and open the pre-start screen.

Outcome: the session exists and the start screen opens. Gaps: T-2, C-2.
Not covered: pressing Start, which waits on the microphone check (see TRAIN-6).

**TRAIN-4.** Actor: a consumer with a marked attempt.
1. (Seam) a marked practice attempt is written for the user.
2. Open the feedback page for it; the domain rating and quoted phrase show.
3. Open the dashboard; the practised count has moved.

Outcome: feedback reads from the rubric, the dashboard reflects the attempt.
Gaps: C-1, T-12 (self practice has no feedback route yet).

**TRAIN-5.** Actor: a consumer.
1. Open settings, change the display name, save, reload; it persists.
2. Open plans; the plans render.

Outcome: profile edits persist. Gaps: A-6.

**TRAIN-6 (skipped).** Actor: a consumer. Steps: start a station, allow the
microphone, talk to the simulated patient, end, wait for marking, read
feedback. Skipped: needs LiveKit workers, and the mic check never resolves in
headless Chrome. Its pieces are covered by TRAIN-3 (set-up), TRAIN-4 (the
marked result) and `verify-voice-station` (the room itself). Gaps: T-7, C-1.

## ASSESS: the institution

| ID | Journey | Local | Spec |
|---|---|---|---|
| ASSESS-1 | Admin schedules a sitting with a circuit and a candidate | yes | `assess/build-sitting.spec.ts` |
| ASSESS-2 | Trainee waits; supervisor starts; the brief opens | yes | `assess/run-circuit.spec.ts` |
| ASSESS-3 | No voice room: supervisor is told, can end the circuit | yes (is the seam) | `assess/run-circuit.spec.ts` |
| ASSESS-4 | Reviewer marks, admin decides and signs off, releases, candidate reads | yes, marked slot seeded | `assess/mark-and-release.spec.ts` |
| ASSESS-5 | Roles: supervisor, trainee and roster boundaries | yes | `assess/roles.spec.ts` |
| ASSESS-6 | Candidate sits a station by voice | no, needs LiveKit | skipped |

**ASSESS-1.** Actor: institution admin.
1. Open Sittings, "New sitting", name it, choose a date.
2. Add a circuit with one station and the roster trainee.
3. The sitting is listed with the circuit assigned.

Outcome: a sitting a supervisor can run. Gaps: B-3, B-5, B-7.

**ASSESS-2.** Actor: trainee, then supervisor.
1. The trainee opens their portal and sees the sitting is not started.
2. The supervisor opens the circuit console and starts it.
3. The brief opens for the trainee.

Outcome: start works and a second Start does not restart it. Gaps: R-2, R-3, S-1.

**ASSESS-3.** Actor: supervisor.
1. After Start, press "Next station".
2. With no voice room, the console shows an alert (voice unavailable).
3. End the circuit; confirm "End the circuit".

Outcome: the failure is stated, and the circuit can still be closed. Gaps: S-1,
S-2, S-7 (open: nothing advances a due circuit when the worker is down).

**ASSESS-4.** Actor: examiner and admin, then the candidate.
1. Circuit ended; (seam) the slot gets an evaluated exam-slot attempt.
2. Before release the candidate sees "Not released yet", and the api returns
   them nothing for the slot review.
3. The reviewer opens the slot review, rates every domain Green, completes it.
4. The admin opens the results row, chooses Pass, writes a rationale, signs off.
5. The admin presses "Release to the candidate" and confirms.
6. The candidate's result page now shows the outcome.

Outcome: release is the only door to the candidate. Gaps: R-1, R-4, R-6.
Finding while building it: after "End the circuit" with no voice, the slot is
skipped and the sitting stays "0 of 1 stations marked" even after a human
review is completed, so no outcome can be decided without the seam.

**ASSESS-5.** Actors: supervisor, trainee, admin.
1. A supervisor sees sittings but not the schedule control (5).
2. A trainee lands on their own portal, not the console (5b).
3. The admin's People page lists the trainee and offers "Add people" (5c).

Outcome: each role sees only what its capabilities grant. Gaps: B-5, R-2, R-6.

**ASSESS-6 (skipped).** Actor: candidate. Steps: join the room, speak to the
patient, the examiner agent closes, scoring runs. Skipped: LiveKit. Covered in
pieces by ASSESS-2/3 and ASSESS-4's seam. Gaps: S-1, S-2, R-5.
