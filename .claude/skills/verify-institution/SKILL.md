---
name: verify-institution
description: How to prove a change to the institution arm works — sittings and circuits, roster, tenancy and org admin, reviews and the result decision workflow, and the domains/assess and domains/platform screens. Use before calling any institution change done.
---

# Verify the institution arm

Pick the **lowest level that can see your change**, run it, and report the
command and its output.

| Your change | Minimum proof |
|---|---|
| A backend rule or route (roster, tenancy, decisions, circuit edit) | Level 1 |
| A permission, a role, anything tenant-scoped | Level 1 + `tests/security` |
| A screen under `domains/assess` or `domains/platform` | Level 1 if the backend changed, then Level 2 |
| Circuit clock, overrides, running a circuit | Level 1 + Level 2 + the circuit flow in `verify-attempt-engine` |
| A response schema | Level 1, regenerate types, then Level 2 |

## Level 1 — backend tests (~4 min, needs the docker services)

```bash
cd api
docker compose up -d            # Postgres :5433, Redis :6380; without them DB tests skip
LIVEKIT_AGENT_NAMESPACE= poetry run pytest -q \
  tests/unit/test_sittings_domain.py tests/unit/test_sittings_domain_edit.py \
  tests/unit/test_sittings_domain_run.py tests/unit/test_roster_domain.py \
  tests/unit/test_tenancy_domain.py tests/unit/test_results_domain.py \
  tests/unit/test_reviews_domain.py \
  tests/repository/test_circuit_run.py tests/repository/test_circuit_jump_race.py \
  tests/repository/test_circuit_overrides.py tests/repository/test_sitting_completion.py \
  tests/repository/test_tenancy_repository.py \
  tests/http/test_sittings_routes.py tests/http/test_sitting_edit_routes.py \
  tests/http/test_circuit_override_routes.py tests/http/test_circuit_tokens.py \
  tests/http/test_roster_routes.py tests/http/test_roster_edit_routes.py \
  tests/http/test_append_trainees_routes.py tests/http/test_tenancy_routes.py \
  tests/http/test_invitations.py tests/http/test_results_routes.py \
  tests/http/test_reviews_routes.py tests/http/test_live_board.py \
  tests/http/test_org_read_models.py tests/http/test_sitting_report.py \
  tests/http/test_sitting_readout_routes.py tests/http/test_exam_import_routes.py \
  tests/http/test_results_export.py tests/http/test_sitting_cancel_routes.py \
  tests/security/test_membership_role_escalation.py
```

457 passed on 2026-09-25. Empty `LIVEKIT_AGENT_NAMESPACE` because a local
`.env` that sets it fails the circuit-token tests without anything being broken.

After a schema change: `make openapi`, then in platform-web
`npm run platform:types` and `npm run types`, then `npm run ci`.

## Level 2 — the screen in a real browser

Use platform-web's `verify` skill (`web/.claude/skills/verify/`):
`doctor.mjs` until it says `ready`, then drive the screen with its harness.
`features/institution.md` has the handles for the dashboard, sittings and
authoring. The test account `walkthrough@example.com` owns `kings` and is
institution admin of `st-marys`; write data only there, and say so in the run log.

Board vs app: a screen drawn from a board in `docs/institution-overhaul/boards/` is proved against it with
`cd web && E2E_REUSE_SERVER=1 npx playwright test e2e/assess/board-home.spec.ts` (part of `npm run e2e:assess`).
`web/e2e/support/board-diff.ts` renders the board (a stand-in `board-runtime.js` replaces the missing
`support.js`), diffs the same region pixel by pixel (under 0.5%, no cluster over 24px), compares computed styles
read from the board's own DOM, and writes PNGs and `scores.json` to `docs/institution-overhaul/verify/board-diff/`.
Add a spec per board with the same helpers. Hide board-only design text on the board side (`.page>.note`, `.page>.meta`, the build-spec `details.fold`, the board's extra tab); set the viewport height to 1700 so element screenshots are not clipped by the app shell; the first run after a long gap may need a minute for the register 429. Data-driven differences (the board ticks earlier steps whatever the data) are listed, not hidden.

Check the request count too: a screen that renders right while looping
requests is still broken. Then run `node scripts/smoke.mjs` if you touched an `api.ts`.

## Traps

- The sitting report (`GET .../sittings/{id}/report`) is `OrgStaff`: a supervisor reads it,
  since review navigation and the step guide need it. Its exports (`report.csv`, the
  readout) stay `OrgAdmin` and the web gates them on `export_results`; record, sign off,
  release and the result PDF stay institution admin (`sign_off_results`).
- A training sitting stops at Mark in `sittingSteps` (no Decide or Release); its slot review reaches the trainee as soon as the reviewer completes it (R-36). A revoked trainee's slot is skipped at dispatch, so no attempt exists for it (R-8).
- A decision is refused on a training sitting (`decision_outside_exam`) and for a candidate with no
  slot `in_consultation` or `completed` (`candidate_did_not_sit`) (R-11). Decision test fixtures
  seat the candidate with `tests.support.decisions.seat_candidate`.
- In an HTTP test a refused request rolls back the shared `db_session`, fixtures included: one
  refusal per test, and last.
- `has_published_exam`/rubric/template count platform rows (`visible_to`), so a setup-checklist
  test retires them in its own transaction rather than assuming none exist.
- `trainee_id` means two things: circuit slots use `users.id`, result decisions use `trainees.id`.
- A platform admin reads any organisation for support but holds none of its
  powers (`OrgAdmin` is `allow_platform_admin=False`). A 403 from the staff
  console on an org-admin route is correct.
- Exam-mode observers are subscribe-only; training-mode supervisors may publish.
- A circuit's clock is never extended for one candidate's `extra_reading_percent`.
- Adding a candidate to a live exam circuit is refused `not_permitted_in_mode` (D7). That is intended.
- `/authoring` redirects to `/authoring/stations`; `<main>` is empty until the
  tablist appears. It is not a broken page.
- Local has no LiveKit credentials: starting a consultation fails (dispatch), but ending a circuit or
  leaving a consultation must still succeed (best-effort room removal). A stuck circuit in reading
  time is a fixture for the sweep: `sweep_circuits` must still succeed and log `sweep: advancing
  circuit failed` for it. Run the job worker (`poetry run python -m app.worker.main`) to see it.
- `GET /orgs/{slug}/circuits/{id}/review` answers 200 `null` until feedback is published, not 404.
- A roster/team row offers "Resend invitation" only while the server says the account is still waiting
  (`invitation_pending` on trainees, `invited` on the member list).
- Browser runs against :3200 should route `/api/v1` straight to :8013 (`.verify/fix-common.mjs` `viaApi8013`).
- An organisation's last administrator cannot be revoked or demoted (`last_admin`, 409). Never revoke
  walkthrough's own st-marys membership to test it without a second admin; `.verify/fix-inst2.mjs`
  proves it on a throwaway org first.
- The recruitment outcome field shows only on an exam-mode sitting's decision; a training sitting
  refuses one (`recruitment_outside_exam`). `.verify/fix-inst2-fixture.mjs` makes an exam sitting in st-marys.
- A proof script that routes through `viaApi8013` must end with `process.exit(...)`, not `process.exitCode`: a left-open
  stream keeps node alive, and the next `uvicorn --reload` on :8013 then hangs at "Waiting for connections to close".
- Absent-by-design reads answer 200 `null`, not 404: a decision before its first draft, a lead or own
  review before its first save, and a candidate's `/me/results/{id}` and `/me/slots/{id}/review` before
  release. A 404 in a proof run on those is a regression, not an expected refusal (B51).
- A candidate's reading brief is `GET /me/slots/{id}/brief` (409 `circuit_not_started` before the circuit
  reaches the slot), for org and library stations alike (B50).
- A rostered trainee holds no membership, so `/app/<org>/trainee/...` is "Page not found" for them and
  `/me/sittings` answers `org_slug: null` (B57, open). `.verify/fix-W1.mjs` seats the candidate as a
  `trainee` member to walk on; it is the end-to-end hire walk (exam sitting, circuit, lead review,
  decision with a recruitment outcome, release, candidate view).
- Seed SCA stations link images on a made-up host; a station copied from one logs
  `ERR_NAME_NOT_RESOLVED` unless the links are stripped (fix-W1 does).
- Trainees now get 403 on staff reads (trainees, cohorts, sittings, programmes, rubrics, templates, review and
  dashboard routes; Phase 1 B4). A proof run that reads one as a candidate must expect 403, not data; the
  trainee portal reads `/me/*` and `/orgs/{slug}/stations` only. An institution admin reads any slot's
  transcript and marking (B7); only a supervisor needs to be named on the circuit.

## Traps found walking a new org
- A capability with `staffHiddenOn` plus `Capability` using `includeHidden` must not 404 staff (guard in `capabilities/registry.ts`).
- A trainee lands on `/app/<org>/dashboard`; `AssessDashboard` must render TraineeHome when `run_circuits` is false.
- An exam circuit is one candidate's sitting. Playwright through a route proxy hangs on SSE: `process.exit` at the end.
- Walking a new org by hand: org registration is only a request. Provision with `POST /api/v1/platform/organizations` and `.../{slug}/memberships` as the platform admin, then read the invitation token from `outbound_messages.payload` (`select payload from outbound_messages where recipient=...`) and open `/accept-invitation?token=...`. A token works once; a second accept is a 422. The wizard saves a draft on step one, so re-running it hits a 409 (now named as "already used by the draft"); resume from the exam row. Paths are `/app/<org>/team`, `/trainees`, `/authoring/exams`, not `/people`. Revoking yourself works when an invited, unaccepted admin remains: restore with `update memberships set status='active', revoked_at=null`.

## Board-diff specs on a second server

- Run your own web server on a spare port and point the spec at it: `E2E_REUSE_SERVER=1 VERIFY_WEB_URL=http://localhost:3107 npx playwright test e2e/assess/<spec> --reporter=line > $TMPDIR/x.txt 2>&1`. Without `E2E_REUSE_SERVER=1` Playwright refuses a port already in use.
- Finished sittings with decisions: `seedResultsOrg` in `web/e2e/support/seed-results.ts` (it has no numeric scores, reviews or real station titles; name those as data exceptions).
- macOS has no `timeout`; `sed -i` needs `''`. A board `.row` with `min-height` is content-box, so match it with `min-h-[<n+29>px]` in the app (border-box).
- `tsc` also reads other agents' `.next-*` folders: filter with `grep -v '^\.next'`.
- A board with a wizard (ScheduleSitting): run one state per foreground call (`--grep "<state> matches ScheduleSitting, desktop" --reporter=line`); a full 26-test run is auto-backgrounded after 180s. Fill the step in the app after moving to it, and re-wrap the board region after the last board click (see exam-day.md, Schedule wizard board spec).
- A decision block scored against a board with the 28px/8px spacing override is dominated by spacing (18%). Score it twice: as shipped (informational) and with `.gap-7`/`.gap-2` overridden to 12px/6px on the app side only (`board-sitting-results.spec.ts`, carries the 10% bar). 14px scored worse than 12px: tune the stand-in by measurement.
- `seedResultsOrg`: `decide(..., null, "draft")` makes an outcome-less draft. `board-slot-review.spec.ts` is `test.fixme` with its baseline until SlotReview is rebuilt.
- Start the web server for board specs with `PLATFORM_API_URL=http://127.0.0.1:8002 NEXT_DIST_DIR=.next-3107 npx next dev --port 3107 --turbopack`; it must run in the background (the only background command).
- Exams board spec: one `--grep` per call on its own port (`NEXT_DIST_DIR=.next-exams npx next dev --port 3104`, run with `VERIFY_WEB_URL=http://localhost:3104 E2E_REUSE_SERVER=1`), `--output $TMPDIR/pw-exams`. Dump text and box rects from both sides to find offsets rather than eyeballing the PNG; the failure PNG in `--output` may show the board, not the app. Tabs 1-5 stay at 10-14% by the spacing exception (see the spec header).
- Before calling a board rewrite done, run `build-sitting.spec.ts` too (pixels never see an `aria-label`). ScheduleSitting logs an as-shipped score (asserted) and a `STAND-IN` score (board rhythm 18/6/10px, no footer divider, extra people rows hidden; never asserted): `bash` loop one `--grep "<state> matches ScheduleSitting, <viewport>"` per call, ~30s each.
- Board seeds share one set of helpers (`web/e2e/support/api.ts`: `createOrg`, `register`, `orgPath`; `db.ts`: `q`, `userIdByEmail`). `register` waits out the sign-up 429 itself, so a spec calls `seedPeopleOrg()` once, with no retry wrapper. Board addresses repeat across runs: `last_login_at` is reset when people are added and set only by `haveSignedIn`. Board invoice numbers use four digits, the api six. `assertLocalDatabase` also refuses `?host=`/`?hostaddr=`/`?service=` in `E2E_DATABASE_URL`.
- Board-diff runs share the api with other lanes' Playwright, so `pgrep playwright` never goes quiet: wait on the output file or `board-diff/scores.json`, one case per call (`--grep "<case>, desktop"`).
- Trainee board specs (`board-trainee*.spec.ts`, `board-self-practice.spec.ts`) sign in as Amara and share one cached org from `seed-trainee.ts` (delete `$TMPDIR/board-trainee-org.json` after changing the seed). Hold `**/join-token` or `JoinRoom` replaces the hero. A review "ready" tab needs a `gp_lead_reviews` row for an exam slot; SelfPractice needs published org stations. After a trainee restyle run `build-sitting.spec.ts` and `run-circuit.spec.ts`; ASSESS-2's "Patient Biodata" failure was identical with the trainee files stashed to HEAD (another lane's uncommitted api/`useCountdown` change), so it is not the restyle.

Running several board specs: `$TMPDIR` and `e2e/.auth/world.json` are shared with other agents, so run one spec per call in the background, writing to a unique `$TMPDIR/inst-<spec>.txt` ending in `done exit=N`, and poll that file (foreground calls time out at 120s). Do not pkill playwright: it may be another agent's run.

## Training room in a real browser
- Use one Playwright context per person (supervisor plus two trainees) so cookies do not collide; trainee password for seeded test accounts is "correct horse battery". Login can 429: retry after a pause.
- The seed may lack an org or programme; add them with the API before scheduling the practice circuit. Use @example.com accounts only.
- Screenshot at 1440 and 390 wide, and assert `document.scrollingElement.scrollHeight <= innerHeight` (the page never scrolls).
- A training room needs LiveKit and the api's `.env` configures it, so `run-circuit.spec.ts` ASSESS-3 (expects no voice) fails locally on an exam circuit; two orgs cannot be made in one pytest test (`root-kings@` collides), so split by test.
