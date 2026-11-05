# Phase 0 results (2026-11-05, local api :8002 + web, working tree with uncommitted exam-day changes)

## e2e
`npm run e2e:assess`: 7 passed, 1 failed, 1 did not run.
- PASS ASSESS-1 build-sitting; ASSESS-4 (3 tests: nothing before release, reviewer completes, admin decides/releases/candidate reads); ASSESS-5, 5b, 5c roles.
- FAIL ASSESS-2 `run-circuit.spec.ts:33`: after Start the trainee sees "Your station is open" / "Connecting to the patient…" / "Leave the room" but the expected text "Patient Biodata" is never rendered (brief not shown; page stays on the connecting state, no LiveKit).
- DID NOT RUN ASSESS-3 (serial after ASSESS-2). Re-run alone it fails at "Next station" not found because the circuit was never started: not a valid result. Unverified.
Hire/partner/roles (`e2e/hire e2e/roles e2e/partner`): 14 passed. HIRE-1, HIRE-2, PARTNER-1, ROLES-1 x9 roles, SWITCH-1..3.

## Journeys
- ASSESS-1 steps 1-3: PASS (spec).
- ASSESS-2 step 1 (trainee sees "Your station opens when your supervisor starts it."): PASS; step 2 (supervisor Start circuit, "Reading time" shown): PASS; step 3 (brief opens, "Patient Biodata"): FAIL as above.
- ASSESS-3: not run (blocked by ASSESS-2). ASSESS-4 steps 1-6: PASS. ASSESS-5 steps 1-3: PASS. ASSESS-6: skipped by design (LiveKit).
- HIRE-1 (menu Overview/Assessments/Results/Now running/Candidates/Build; no Sittings/People): PASS. HIRE-2 (candidate sees My assessments only): PASS.
- PARTNER-1: PASS.

## Screenshots
59 full-page PNGs in `baseline/{admin,supervisor,trainee,hire-admin,hire-candidate,partner}/`; per-page status and h1 in `baseline/screenshots.log`. Taken from the e2e world (org e2e-<id>), as the README's seed-demo-org step fails: `POST /orgs/st-marys/sittings -> 409 programme_not_active` (the seed creates the programme but it is not active).
Not captured (state-dependent dialogs, row-action menus, tabs beyond the first, empty/error states): inventory entries for those are [code] only, not confirmed in the browser. Supervisor/trainee run-time states (started circuit, live board with a running circuit, released result, review) not captured either.

## Browser findings that differ from the route list
- `/authoring` redirects to `/authoring/rubrics`; `/authoring/feedback-templates` and `.../feedback-templates/new` also land on the rubrics section (no list URL for feedback templates).
- `/team` renders the People screen (h1 "People") for the admin; hire `/team` renders "Candidates".
- `/stations` as admin redirects to `/mocks` (h1 "Practice"); only the trainee sees "Station library" there.
- Supervisor can open Authoring and Settings and People pages (200); nothing was clicked to see which controls are hidden.
- Partner overview h1 is "<ORG NAME> dashboard" (upper-cased slug in the e2e world).
- Hire `/team` shows Candidates, and hire wording leaks hard-coded "sitting"/"trainee" literals (see INVENTORY part 5).
