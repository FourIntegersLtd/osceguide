# Hire arm inventory

Every hire screen, its route, role, board and the platform-api calls it makes, with the refusal
codes it must word. Generated from the API panel on each board in `boards/` (canvas
https://claude.ai/artifact/NzjwRSZGW1tUA4G3WjNL59). If a board changes, regenerate this table.
Plan: `~/.claude/plans/i-want-us-to-tidy-pelican.md`.

`{o}` = `/api/v1/orgs/{org_slug}`. `…/x` is a sibling of the row above it.

Decisions (2026-11-06): hire stays exam mode with no new entity, API or migration; employers keep
Formal exam and Training; the hiring outcome shows only when the arm is hire **and** the mode is exam,
and never to the candidate. **Signed off (2026-11-07):** the boards and "Rotation" as the hire word for
circuit.

## Words

| Institution | Hire |
|---|---|
| Sitting | Assessment |
| Trainee | Candidate |
| Supervisor / GP lead | Assessor / Lead assessor |
| Year group (cohort) | Intake |
| Home | Overview |
| My training | My assessments |
| Circuit | Rotation |

Exam, Marking scheme, Station, Domain and Competency are the same on both arms.

## Screens

| Board | Screen | Route · role · owner | API calls | Refusal codes it words |
|---|---|---|---|---|
| HireRegister | Register an employer | Route /register/organisation · public · NewOrganisation.tsx · owner institution-owner | `POST /api/v1/site/messages` | `invalid_message`, `invalid_input` |
| HireAcceptInvite | Accept an invitation | Route /accept-invitation · public · owner access-owner (words: institution-owner) | `GET /api/v1/auth/invitation/{token}`<br>`POST /api/v1/auth/register`<br>`POST /api/v1/auth/login`<br>`POST /api/v1/auth/switch-workspace` | `invitation_not_pending`, `email_taken`, `weak_password`, `invalid_credentials`, `trainee_revoked` |
| HireHome | Hire overview | Route /app/[w]/dashboard · admin · replaces the OrgDashboard.tsx:212-223 hybrid and the duplicate branch at :122-133 · owner institution-owner | `GET {o}/dashboard`<br>`GET {o}/results`<br>`GET {o}/supervisor/circuits`<br>`GET /api/v1/me/capabilities` | `forbidden`, `not_a_member` |
| HireAssessorHome | Assessor overview | Route /app/[w]/dashboard · assessor (supervisor role) · owner institution-owner | `GET {o}/supervisor/circuits`<br>`GET {o}/dashboard` | `forbidden`, `lead_cannot_run` |
| HireExams | Exams | Route /app/[w]/authoring/exams · admin · capabilities/authoring · owner content-owner (words come from capabilities/ after M5) | `GET {o}/exams`<br>`POST {o}/exams`<br>`PATCH {o}/exams/{exam_id}`<br>`DELETE {o}/exams/{exam_id}`<br>`POST {o}/exams/{exam_id}/publish`<br>`POST {o}/exams/{exam_id}/retire` | `exam_in_use`, `exam_not_publishable`, `exam_code_taken`, `invalid_exam_code`, `invalid_exam_settings` |
| HireNewExam | New exam | Routes /app/[w]/authoring/exams/new, /programmes · admin · owners content-owner (exam), institution-owner (programme) | `GET {o}/exams/catalog`<br>`POST {o}/exams/import`<br>`POST {o}/exams`<br>`GET {o}/programmes`<br>`POST {o}/programmes`<br>`PATCH {o}/programmes/{id}` | `exam_already_imported`, `programme_exists`, `exam_code_taken`, `unknown_exam` |
| HireExamDetail | Exam detail | Routes /app/[w]/authoring/exams/[id] and its settings · admin · owner content-owner | `GET {o}/exams`<br>`PATCH {o}/exams/{exam_id}`<br>`GET {o}/programmes`<br>`PATCH {o}/programmes/{id}`<br>`GET {o}/rubrics`<br>`GET {o}/stations` | `exam_rubric_not_ready`, `invalid_exam_settings`, `programme_not_active`, `programme_not_found`, `exam_in_use` |
| HireSchemeVersions | Marking schemes | Routes /app/[w]/authoring/rubrics, /new · admin · owner content-owner (builder), marking-owner (scheme rules) | `GET {o}/rubrics`<br>`POST {o}/rubrics`<br>`POST {o}/rubrics/copy`<br>`GET {o}/rubrics/starting-points`<br>`PATCH {o}/rubrics/{rubric_id}`<br>`POST {o}/rubrics/{id}/versions/{v}/archive` | `rubric_not_found`, `invalid_rubric`, `not_archivable` |
| HireMarkingScheme | Marking scheme builder | Route /app/[w]/authoring/rubrics/[id]/versions/[v] · admin · the v3 builder from the institution canvas (SchemeBuilder board) unchanged; hire words only (assessor, candidate) · owner content-owner | `GET {o}/rubrics/{rubric_id}`<br>`POST {o}/rubrics/{id}/versions`<br>`PATCH {o}/rubrics/{id}/versions/{v}`<br>`POST {o}/rubrics/{id}/versions/{v}/publish`<br>`POST {o}/rubrics/preview`<br>`POST {o}/rubrics/draft-instructions`<br>`GET {o}/rubrics/trial-candidates`<br>`POST {o}/rubrics/{id}/versions/{v}/trial` | `stale_revision`, `not_editable`, `already_published`, `invalid_rubric`, `rubric_version_not_found`, `invalid_trial_transcript`, `marking_not_ready` |
| HireStations | Stations | Routes /app/[w]/authoring/stations, /new, /import · admin · import progress arrives on the existing event stream, never polled · owner content-owner | `GET {o}/stations`<br>`POST {o}/stations`<br>`POST {o}/stations/autogenerate-draft`<br>`GET {o}/station-imports`<br>`POST {o}/station-imports`<br>`GET {o}/station-imports/{import_id}`<br>`POST {o}/station-imports/{import_id}/station`<br>`GET {o}/station-templates` | `invalid_import_file`, `import_not_ready`, `station_import_not_found`, `generation_unavailable`, `generation_empty`, `template_not_published` |
| HireStationBuilder | Station builder | Route /app/[w]/authoring/stations/[id] · admin · owner content-owner | `POST {o}/stations/{id}/versions`<br>`PATCH {o}/stations/{id}/versions/{v}`<br>`DELETE {o}/stations/{id}/versions/{v}`<br>`PATCH …/versions/{v}/brief`<br>`POST …/versions/{v}/photos`<br>`POST …/versions/{v}/photos/remove`<br>`POST …/versions/{v}/publish`<br>`POST …/versions/{v}/archive`<br>`GET {o}/station-versions/{version_id}/sections` | `not_editable`, `already_published`, `draft_exists`, `station_empty`, `invalid_photo`, `photo_storage_unavailable`, `not_deletable`, `version_not_found` |
| HireLayoutBuilder | Station layout | Routes /app/[w]/authoring/station-templates[/id] · admin · the institution layout builder unchanged · owner content-owner | `GET {o}/station-templates`<br>`POST {o}/station-templates`<br>`POST {o}/station-templates/{id}/copy`<br>`POST {o}/station-templates/{id}/versions`<br>`PATCH …/versions/{v}`<br>`DELETE …/versions/{v}`<br>`POST {o}/station-templates/{id}/publish`<br>`POST …/versions/{v}/archive` | `station_template_not_found`, `station_template_version_not_found`, `not_editable`, `already_published`, `not_archivable` |
| HireCandidates | Candidates | Route /app/[w]/trainees · admin · fixes the institution copy on this page today · owner institution-owner | `GET {o}/trainees`<br>`POST {o}/trainees`<br>`POST {o}/trainees/bulk`<br>`POST {o}/trainees/bulk/cohort`<br>`POST {o}/trainees/bulk/resend-invitation`<br>`POST {o}/trainees/bulk/revoke`<br>`PATCH {o}/trainees/{id}`<br>`DELETE {o}/trainees/{id}`<br>`POST {o}/trainees/{id}/access`<br>`POST {o}/trainees/{id}/anonymise`<br>`POST {o}/trainees/{id}/resend-invitation`<br>`GET {o}/cohorts`<br>`GET {o}/trainee-groups[/{id}/members]`<br>`GET {o}/entitlements` | `trainee_exists`, `trainee_revoked`, `trainee_in_use`, `too_many_trainees`, `cohort_exists`, `cohort_in_use`, `invitation_not_pending`, `invalid_email` |
| HireAssessors | Assessors | Route /app/[w]/team · admin · owner institution-owner | `GET {o}/memberships`<br>`POST {o}/memberships`<br>`POST {o}/memberships/bulk`<br>`PATCH {o}/memberships/{id}`<br>`POST {o}/memberships/{id}/revoke`<br>`POST {o}/memberships/{id}/restore`<br>`POST {o}/memberships/{id}/resend-invitation`<br>`GET {o}/audit` | `membership_exists`, `membership_not_found`, `invitation_pending`, `invitation_not_pending`, `last_admin`, `cannot_revoke_own_console_access`, `not_a_member` |
| HireAssessments | Assessments | Route /app/[w]/sittings · admin · owner institution-owner | `GET {o}/sittings`<br>`GET {o}/programmes` | `forbidden`, `unavailable` |
| HireScheduleAssessment | Schedule an assessment | Route /app/[w]/sittings/new · admin · owner institution-owner | `GET {o}/programmes`<br>`GET {o}/trainees`<br>`GET {o}/cohorts`<br>`GET {o}/trainee-groups`<br>`GET {o}/memberships`<br>`POST {o}/roster/resolve`<br>`POST {o}/sittings`<br>`POST {o}/sittings/{id}/circuits/bulk` | `programme_required`, `exam_rubric_not_ready`, `not_permitted_in_mode`, `invalid_circuit`, `trainee_already_on_circuit`, `trainee_not_on_roster`, `trainee_revoked`, `too_many_trainees` |
| HireAssessment | Assessment | Route /app/[w]/sittings/[id] · admin · owner institution-owner | `GET {o}/sittings/{id}`<br>`PUT {o}/sittings/{id}`<br>`POST {o}/sittings/{id}/cancel`<br>`GET {o}/sittings/{id}/report`<br>`GET {o}/cohorts`<br>`GET {o}/trainees`<br>`PUT {o}/circuits/{id}`<br>`DELETE {o}/circuits/{id}` | `sitting_not_found`, `sitting_locked`, `circuit_locked`, `circuit_not_found`, `circuit_already_ended`, `stale_revision` |
| HireEditRotation | Edit rotation | Routes /app/[w]/sittings/[id]/circuits/new, /circuits/[id]/edit · admin · "Rotation" needs sign-off · owner institution-owner | `POST {o}/sittings/{id}/circuits`<br>`PUT {o}/circuits/{id}`<br>`GET {o}/circuits/{id}/edit-lock`<br>`GET {o}/stations`<br>`GET {o}/memberships` | `circuit_locked`, `circuit_already_ended`, `invalid_circuit`, `trainee_already_on_circuit`, `station_not_on_circuit`, `lead_cannot_run`, `stale_revision` |
| HireNowRunning | Now running | Route /app/[w]/live · admin and assessor (own rotations) · owner institution-owner | `GET {o}/live`<br>`SSE {o}/live/stream`<br>`GET {o}/live/history` | `forbidden`, `unavailable` |
| HireConsole | Rotation console | Route /app/[w]/circuits/[id] · assessor and admin · start belongs to attempt-engine; the workflow to institution-owner | `GET {o}/circuits/{id}/console`<br>`SSE {o}/circuits/{id}/console/stream`<br>`GET …/review, …/interventions`<br>`POST …/start, pause, resume`<br>`POST …/advance, jump-to, redo-station`<br>`POST …/resend-patient, reset-clock, extend-clock`<br>`POST …/end, observer-token`<br>`PATCH …/auto-advance`<br>`POST …/review/finalize` | `circuit_not_started`, `circuit_not_live`, `circuit_paused`, `circuit_not_paused`, `circuit_already_ended`, `no_active_station`, `lead_cannot_run`, `circuit_review_finalized`, `review_incomplete`, `reviews_pending`, `voice_unavailable` |
| HireStationReview | Mark a station | Route /app/[w]/slots/[id]/review · assessor, lead assessor · owner marking-owner | `GET {o}/slots/{s}/reviews/mine`<br>`PUT {o}/slots/{s}/reviews/mine`<br>`DELETE {o}/slots/{s}/reviews/{id}`<br>`GET {o}/slots/{s}/gp-lead-review`<br>`PUT {o}/slots/{s}/gp-lead-review`<br>`DELETE {o}/slots/{s}/gp-lead-review`<br>`POST {o}/slots/{s}/marking/retry`<br>`GET /attempts/{id}/transcript` | `not_slot_reviewer`, `review_locked`, `review_conflict`, `review_not_draft`, `review_incomplete`, `invalid_rating`, `nothing_to_review`, `circuit_review_finalized`, `marking_not_ready`, `slot_not_found` |
| HireResults | Results | Route /app/[w]/results · admin · owner institution-owner | `GET {o}/results` | `forbidden`, `unavailable` |
| HireDecisions | Hiring decisions | Route /app/[w]/sittings/[id]/results · admin · follow-up: a hired list across assessments needs an api filter · owner institution-owner (scores: marking-owner) | `GET {o}/sittings/{id}/report`<br>`GET …/cohort, …/readout`<br>`GET …/candidates/{t}/decision`<br>`PUT …/candidates/{t}/decision`<br>`POST …/sign-off`<br>`POST …/release, …/decisions/release`<br>`GET …/result-preview, …/result.pdf, …/report.csv`<br>`GET {o}/slots/{s}/reviews` | `recruitment_outside_exam`, `decision_outside_exam`, `decision_revised`, `evidence_changed`, `incompatible_outcomes`, `invalid_workflow`, `not_signable`, `reviews_pending`, `outcome_not_releasable`, `candidate_did_not_sit`, `result_not_found`, `not_an_exam_sitting`, `stale_revision` |
| HireReporting | Reporting | Route /app/[w]/reporting · admin · owner institution-owner | `GET {o}/reporting` | `forbidden`, `unavailable` |
| HireSettings | Settings | Route /app/[w]/settings · admin · SSO and MFA belong to access-owner; the page to institution-owner | `GET {o}`<br>`PATCH {o}`<br>`PATCH {o}/mfa-policy`<br>`GET {o}/sso-status`<br>`GET {o}/entitlements` | `sso_not_configured`, `sso_only_password_members`, `mfa_required_by_policy`, `invoice_not_found`, `receipt_not_found`, `stale_revision` |
| HireCandidateHome | My assessments | Route /app/[w]/trainee · candidate · owner institution-owner | `GET /me/sittings`<br>`SSE /me/sittings/stream`<br>`POST /me/circuits/{id}/join-token` | `circuit_not_live`, `circuit_paused`, `attempt_not_joinable`, `voice_unavailable`, `trainee_revoked` |
| HireCandidateAssessment | Your assessment | Route /app/[w]/trainee/sittings/[id] · candidate · owner institution-owner | `GET /me/sittings`<br>`SSE /me/sittings/stream`<br>`GET /me/slots/{id}/brief`<br>`POST /me/circuits/{id}/join-token` | `circuit_not_started`, `circuit_not_live`, `circuit_paused`, `no_active_station`, `slot_not_found`, `slot_locked` |
| HireCandidateRoom | Station room | Route attempts/[id] (runner) · candidate · owner attempt-engine-owner | `POST /attempts`<br>`GET /attempts/{id}`<br>`SSE /attempts/{id}/stream`<br>`GET /attempts/{id}/brief`<br>`POST /auth/stream-ticket` | `attempt_not_joinable`, `attempt_in_progress`, `attempt_not_ready`, `attempt_not_yours`, `invalid_attempt_state`, `voice_unavailable`, `circuit_paused` |
| HireCandidateResult | Your result | Route /app/[w]/trainee/results/[id] · candidate · owner institution-owner | `GET /me/results/{id}`<br>`GET /me/results/{id}.pdf`<br>`POST /me/results/{id}/acknowledge` | `result_not_released`, `result_not_found`, `outcome_not_releasable` |
| HireCandidateReview | Station feedback | Routes /app/[w]/trainee/reviews/[id], attempts/[id] · candidate · owner institution-owner (feedback text: marking-owner) | `GET /me/slots/{id}/review`<br>`GET /attempts/{id}/transcript` | `result_not_released`, `review_not_found`, `slot_not_found`, `attempt_not_yours` |
| HireRefused | Not on this account | Any hire role · owner web-foundation-owner (surfaces/hire/surface.ts screenNames) | none | `trainee/practice`, `stations/[id]/practise`, `mocks/**` |

## Checks run on this table

- Every `/api/v1` path on the boards exists in `api/openapi.json` (script check, 2026-11-06; the
  console's short sibling names were checked under `{o}/circuits/{id}/`).
- Every board in `canvas.json` has a file, and every link between boards resolves.
- Built in the worktree (uncommitted): vocabulary and words-aware `errorCopy`, `HIRE_SCREEN_NAMES` + `NotOnThisAccount`, a "Hiring" group in the workspace switcher, `seed-demo-org.mjs --employer` (Acme Health Trust, `acme-health-trust`), Sittings presets and Next step, Results Where-it-is, Team role labels, cohort dialogs, JoinRoom refusals.
- Still to do: MyReview and trainee screens beyond JoinRoom refusals; LiveNow/People residue; the reverse direction.
  Phase 3 reverse direction: Every page reachable on hire maps to a board above
  or to HireRefused, and every refusal code above has a hire-worded line in `errorCopy.ts`.

## Hire Part 2: built and still needs api

Built (web only, uncommitted): first-assessment checklist on HireHome (`HireSetup.tsx`, `hireSteps.ts`); rotations dealt automatically to assessors in HireScheduleAssessment (`RotationBuilder.tsx`, `rotations.ts`); ranked candidate comparison with a required reason for a hire on HireDecisions (`CandidateRanking.tsx`, `ranking.ts`); wizard step labels in hire words (`scheduleWords`). Proof: `web/e2e/assess/hire-part2.spec.ts` at 1440 and 390.

Still needs api: per-station assessors; staggered start times; server-enforced hire rationale (today the browser requires it); candidate reminders and tech-check link; no-show and dropped-connection actions with audit trail; exam templates; CSV shortlist export; appeals and re-mark; data retention and delete-on-request.

## Follow-ups (out of scope)

- A list of hired candidates across assessments needs a filter on `{o}/results`.
- The assistant's `employer` surface is refused by the backend today.
