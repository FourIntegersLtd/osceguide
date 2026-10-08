# Experience gaps: the source of truth

Checked against commit 07aab19 (2026-10-07). Ten read-only sweeps enumerated every page under
`web/src/app` (83 workspace and auth pages, 28 staff console pages) and every api router (63
files), per role, per load, per action and per error code, plus state over time (entitlements,
organisation and person lifecycle, catalogue versions, jobs, concurrency, scale) and
cross-cutting checks (surface manifests, the error-code union, email templates). Nothing was
run; items only a staging run can prove are in section 12, not omitted.

**How to use this file.** Every fix cites a row ID and flips its Status. A new finding gets the
next ID in its area. Nobody re-audits an area without first reading its rows. The fix loop is
`.claude/skills/fix-experience-gaps/SKILL.md`. `web/docs/BACKLOG.md` is the build list; this is
the breakage list; BACKLOG rows that this file absorbs carry the ID here.

**Severity.** BLOCKS: cannot complete, wrong data, or security. WRONG: silent failure, false
copy, or data left inconsistent. ROUGH: confusing, or a dead end with a workaround.

**Status.** open | decided (design agreed, not built) | fixed <commit> | needs-staging |
re-check (another session was editing the cited file when the sweep ran).

**Decisions taken 2026-10-07.** Training sittings share a slot review when the reviewer marks
it complete (no sign-off, no release). Team invites and roster adds gain the platform seat
route's temporary password for brand-new accounts. The Resend sender domain is an ops task.

**Evidence paths** are relative to `api/app/features/`, `api/app/core/` or `web/src/`
unless written in full.

## Sessions log

| Date | Area | Fixed | Left open and why |
|---|---|---|---|
| 2026-10-07 | institution lane, round 1 | R-1 R-2 R-3 S-1 R-4 B-3 (d1b5c11) | none; openapi regen pending |
| 2026-10-07 | content lane, round 1 | B-2 S-3 T-1 T-2 C-1 C-2 (0dfc592) | none |
| 2026-10-07 | access lane, round 1 | A-1 A-2 A-3 F-1 S-4 S-6 (9593584) | F-1 and S-4 schema follow-ups listed in their rows |
| 2026-10-07 | content lane, round 2 | B-6 B-8 C-3 C-4 C-5 C-6 (b1b43bc) | B-8 and C-4 partly; /me/entitlements trial field needs openapi regen |
| 2026-10-07 | content lane, round 3 | F-2 C-7 C-8 C-9 C-10 C-11 (c2835df) | C-9 partly (no UI for the error); SelfPracticeStation title restore left to institution lane |
| 2026-10-07 | institution lane, round 2 | R-6 B-7 S-9 B-4 R-21 R-22 (40b599b) | too_many_trainees needs openapi regen; no browser check |
| 2026-10-07 | content lane, round 4 | C-9 C-12 C-13 C-14 C-16 (04f288c) | C-4 needs started_at on AttemptBrief; C-12, C-14 partly |
| 2026-10-07 | institution lane, round 3 | B-5 R-36 R-8 R-9 R-10 (80bfee0) | new error codes need openapi regen; no browser check |


## 1. Fix first: the BLOCKS rows, in order

- **R-1** · BLOCKS · fixed d1b5c11 (test_an_exam_candidate_reads_nothing_of_their_slot_until_release) · Exam candidate reads machine marks and transcript before release (owner path has no release or mode gate; /me/sittings fills attempt_id for every mode). attempts/service_access.py:40; dashboard/service_trainee.py:97; MySittingDetail.tsx:191
- **A-1** · BLOCKS · fixed 9593584 (revokeSession.test.ts) · Sign-out never revokes the refresh token: DELETE /api/session posts /auth/logout with no bearer and ignores the 401. web/src/app/api/session/route.ts; identity/router.py /auth/logout
- **R-2** · BLOCKS · fixed d1b5c11 (test_a_trainee_cannot_open_the_console_stream) · Trainees can subscribe to the circuit console SSE stream (may_read_org_policy admits trainees; REST console is OrgStaff) and read every candidate's name, email and review flags. dashboard/router.py:197; service_streams.py
- **R-3** · BLOCKS · fixed d1b5c11 (test_pressing_start_again_leaves_a_running_circuit_where_it_is) · Starting a circuit twice restarts it: ensure_startable refuses only ended circuits, so a second Start resets started_at and Reading on slot 0 with the patient still in the room. sittings/domain.py:170-173; SupervisorControls.tsx:100-113
- **S-1** · BLOCKS · fixed d1b5c11 (test_a_suspended_organisation_lets_nobody_into_the_room, test_a_revoked_trainee_cannot_join_their_circuit) · join_token_for_trainee checks only the roster slot: suspended org, revoked access or removed membership can still join a live circuit. sittings/service_join.py; repository_run.py circuit_for_rostered_trainee
- **R-4** · BLOCKS · fixed d1b5c11 (test_a_signed_off_result_locks_the_reviews_behind_it) · Reviews and the lead's review are not locked after sign-off or release; the candidate reads whatever is edited later. reviews/service.py
- **B-1** · BLOCKS · fixed 610efab (test_a_team_invite_may_hand_a_new_account_a_temporary_password, test_a_roster_add_may_hand_a_new_account_a_temporary_password; bulk import stays email-only) · Nobody after the first admin can get in: team invite and roster add are email-only, Resend domain unverified, temporary password only on the platform seat route, nothing shows delivery failure. team/InvitePanel.tsx; roster/service.py; 87cbc95. 
- **B-2** · BLOCKS · fixed 0dfc592 (test_org_staff_browse_the_platform_library_of_an_exam_their_org_offers, libraryPaging.test.ts) · Circuit builder empty for platform exams: require_exam_access uses the staff member's personal entitlements, 403 becomes an empty page. stations/service_library_reads.py:44; entitlements/service_access.py:22-35; libraryPaging.ts
- **B-3** · BLOCKS · fixed d1b5c11 (test_a_draft_programme_does_not_count_as_ready) · Draft programme counts as ready: setup ticks "Programme", NewSitting says "Activate a programme first". catalog/repository.py:276-288; NewSitting.tsx:56-98
- **B-4** · BLOCKS · fixed 40b599b (programmes/support.test.ts; Adopt on the Programmes page) · An org cannot adopt a platform exam: GET /orgs/{slug}/exams/catalog and POST .../exams/import have no web caller, so the exam setup step needs a hand-made exam. catalog/router.py; schema.d.ts only
- **R-5** · BLOCKS · fixed 1b2f457 · Scoring failure is invisible: EvaluationFailed re-raised with no retry, attempt stays interaction_complete, staff rail reads "not ready yet" forever, rescore only on the platform console. attempts/jobs.py:129; slotReviewSteps.ts:20-35
- **S-2** · BLOCKS · fixed 1b2f457 · A slot attempt with no frozen definition or an unpublished rubric runs but enqueue_scoring only logs; never marked, nobody told. attempts/service_render.py _marking_snapshot; enqueue_scoring
- **S-3** · BLOCKS · fixed 0dfc592 (test_a_version_in_a_practice_set_cannot_be_archived; archive refused with not_archivable; unfinished-circuit case untested) · Station archived while on a circuit or in a set: archive_version checks no usage, runnable_station raises station_not_published at the slot. stations/service_versions.py
- **R-6** · BLOCKS · fixed 40b599b (test_sitting_report: report is for staff of this organisation only) · Results page: report route is OrgAdmin and sign-off/release/PDF OrgInstitutionAdmin, supervisors 403 on the page, partner admins see release controls that 403. Results.tsx:56-99; results/router.py
- **B-5** · BLOCKS · fixed 80bfee0 (test_a_supervisor_is_not_offered_authoring_writes; author_content capability) · Supervisors see every authoring write control (templates, stations, exams edit/publish/delete, rubrics, programme edit, version history) and each returns 403. StationTemplatesSection.tsx:100-222; StationsSection.tsx; ExamsSection.tsx; RubricDetail.tsx; ProgrammesSection.tsx; StationVersionHistory.tsx
- **B-6** · BLOCKS · fixed b1b43bc (versions.test.ts canManageTemplate) · Platform-owned templates seen from an org offer Publish/Archive/Delete that always end in station_template_not_found. StationTemplatesSection.tsx:170-216,383-420; repository_templates.py:55-82
- **B-7** · BLOCKS · fixed 40b599b (bulkImport.test.ts chunks of 500; test_an_import_over_the_limit_names_the_limit) · Roster CSV over 500 rows rejected whole, no chunking, generic message. roster/api.ts:78-83; BulkImportDialog.tsx:84-100; roster/schemas.py:54,64
- **B-8** · BLOCKS · partly fixed b1b43bc (paths.test.ts: wizard opens with the exam prefilled; the template publish step remains and is now explained) · Template-less station for an org's own exam: needsTemplateForLayout, the only way out is a wizard that asks for the exam again and a publish step. useCreateStationForm.ts:96-110,236; CreateStationScreen.tsx:232-247
- **T-1** · BLOCKS · fixed 0dfc592 (practisableStation.test.ts) · SelfPracticeStation renders a blank page for a missing, draft or other-org station. domains/assess/trainee/SelfPracticeStation.tsx
- **T-2** · BLOCKS · fixed 0dfc592 (startFailure.test.ts) · Self practice after the trial dies with a bare red error; not_entitled handled only in MockSetup; the org grant is the only way on. attempts/service.py:73; StationScreen.tsx:308; MockSetup.tsx:114
- **S-4** · BLOCKS · fixed 9593584 (test_billing_routes.py unknown-address payment kept for support; a move-to-account route needs schema) · Stripe checkout.session.completed whose customer_email does not match an account raises InvalidWebhook: charged, no access. billing/service.py _apply_checkout
- **S-5** · BLOCKS · fixed 1f7e50d · Mail outage over ~15 minutes: after 6 attempts a message is abandoned and only logged (invitations, resets with 1h expiry, receipts lost). notifications mark_failed, MAX_ATTEMPTS
- **S-6** · BLOCKS · fixed 9593584 (test_rate_limit.py cohort behind one address) · Cohort signing in from one NAT at exam start: SIGN_IN is 10 per 60s per IP and fails closed. core/rate_limit.py SIGN_IN, caller_key
- **S-7** · BLOCKS · open (design choice: the api must advance due circuits itself, on read or with an in-api sweeper, when the worker is down; clock_overdue alert and /platform/health heartbeat already make it visible) · Worker down freezes every running circuit; S-8 score_attempt failure has no retry (same as R-5; S-8 fixed 1b2f457, worker-down part open). worker/main.py; attempts/jobs.py
- **S-9** · BLOCKS · fixed 40b599b (latecomers.test.ts 300 rows over 3 pages) · Roster or team over 100 in the circuit pickers: first page only, trainees with no user_id dropped. NewCircuit.tsx:35-39; EditCircuit.tsx:51-52; AddTraineesDialog.tsx:50
- **A-2** · BLOCKS · fixed 9593584 (ssoCallback.test.ts; not checked against a live Entra tenant) · Entra SSO fails every sign-in: the callback page never sends state and _requires_state(ENTRA) rejects a missing one. SsoCallback.tsx; sso/service_login.py
- **A-3** · BLOCKS · fixed 9593584 (browser proof .verify/fix-access-batch.mjs) · /register and /forgot-password have no hydration guard and no method="post": an early native submit puts the password in a GET URL. Register.tsx; ForgotPassword.tsx
- **F-1** · BLOCKS · fixed 9593584 (orgSuspension.test.ts; org status on MembershipRead would show the screen before the first refusal: needs schema) · organization_suspended is never handled by the web: suspended-org members get the shell with raw 403 per panel; vocabulary says "cannot sign in", which is false. core/tenancy.py:36; vocabulary.ts:37
- **H-1** · BLOCKS · partly fixed c3983f0 (employer org provisioned by staff, hire nav to real routes; public NewOrganisation has no create route behind it, so self-serve employer signup stays open) · The hire surface cannot exist: org_type pattern is ^(institution|partner)$, NewOrganisation "Employer" ends in "Nothing was created"; the hire nav links authoring, summary and discussion to notFound and "Assessments" to a 403 for candidates. tenancy/schemas.py:135; workspace.ts:40-44; NewOrganisation.tsx; surfaces/hire/surface.ts; OrgDashboard.tsx:178-186; TraineeHome.tsx:197-207
- **H-2** · BLOCKS · open (product decision: there is no partner-admin role and PILOT_PARTNERS is the money attribution gate; opening the dashboard to other partners or non-reporters needs a decision and likely a migration) · Partner dashboard 403s for any partner admin who is not a reporter (ensure_reporter), and 404s for any partner other than bmj (PILOT_PARTNERS). growth/service.py:107; growth/domain.py:15
- **F-2** · BLOCKS · fixed c2835df (refRoutes.test.ts; /help page added) · Help station cards link to /stations/{slug}, a route that does not exist; /help is declared with no page. help/refRoutes.ts; help/capability.ts
- **P-1** · BLOCKS · fixed 610efab (test_an_admin_cannot_revoke_their_own_console_access; caller is always an admin so the self guard also prevents zero admins) · A platform admin can revoke their own console access; set_platform_admin has no self or last-admin guard. tenancy/router_platform_users.py; user/AccountTab.tsx
- **P-2** · BLOCKS · fixed a451a1e (test_delete_progress_keeps_exam_slot_attempts) · User > Stations > delete progress deletes exam_slot attempts and released results (no kind filter). attempts/repository_platform.py:113
- **P-3** · BLOCKS · fixed a451a1e (test_a_version_an_exam_is_marked_against_cannot_be_archived, test_archiving_the_current_version_falls_back_to_the_previous_published_one) · Rubric Archive is one click, no confirm, no in-use check; archiving the current version strands the rubric until a new draft is published. RubricDetail.tsx; rubrics/service.py:266-285; core/lifecycle.py:100-115
- **P-4** · BLOCKS · fixed 969f64b · Media list Publish has no confirm and no pipeline gate; a published item can be neither unpublished nor deleted; a crashed worker leaves an item locked with no reaper. MediaListTable.tsx; media/service.py:137-155; MediaDetailScreen.tsx
- **P-5** · BLOCKS · fixed c6bbf14 (test_a_revoked_reporter_can_be_added_again_and_a_live_one_twice; copy no longer promises an email) · Growth "Add viewer" says an email with a password is sent; it only inserts a row; re-adding a revoked viewer hits a unique constraint with an opaque failure. ReportersPanel.tsx; growth/service.py:385-390; models.py:62
- **P-6** · BLOCKS · fixed c3983f0 (test_restoring_a_lapsed_organisation_is_not_undone_by_the_next_sweep, test_renewing_to_a_past_date_is_refused; confirm warns generically, no live-sitting count) · Suspend has no confirm or live-sitting warning; Restore leaves contract_ends_at so the hourly sweep re-suspends; renewContract accepts a past date. OrganizationDetail.tsx; tenancy/service_platform.py
- **P-7** · BLOCKS · fixed a451a1e (test_platform_job_actions_routes.py, jobs.test.ts) · Ops: no retry for any non-marking failed job; list is one page of 50; stalled jobs show no age and have no cancel. health/router_platform.py:51-67; Ops.tsx
- **P-8** · BLOCKS · fixed 610efab (test_the_console_reissues_a_password_only_until_it_is_changed, temporaryPassword.test.ts) · Temporary-password seat: password cannot be seen or copied again, no re-issue, no client strength check. SeatMemberPanel.tsx
- **P-9** · BLOCKS · partly fixed c6bbf14 (P-10 MFA reset button with confirm and P-11 SAML section in the org SSO tab, web only, no test; the P-9 reply UI is in MessagesInbox.tsx, the user's own uncommitted inbox work, left to it) · /staff/messages has no reply UI (route exists); P-10 MFA reset route has no web caller; P-11 SAML org form routes have no web caller. MessagesInbox.tsx; public_site/router.py:106-119; tenancy/router_platform_users.py; sso/router.py:125-260. All re-check (other session).

## 2. Institution staff: build (B-*)

- **B-9** · WRONG · fixed 9e7e86f (roster tabs test: a supervisor is not offered the Exam access tab) · Exam access tab 403s for supervisors (route OrgAdmin, tab gated only on the grant form). Roster.tsx:25-31; AccessPanel.tsx:48-52; entitlements/router.py:38-44
- **B-10** · WRONG · open (by design: practice-access lacks ends_at, paging and search the Exam access tab needs, so both route sets stay, see entitlements/README.md; invite-unknown-address and bulk grant still have no screen) · Org practice-access routes (list, grant, bulk, revoke, expiry) have no web caller; the web uses the older /entitlements routes. entitlements/router.py:91-152
- **B-11** · ROUGH · fixed 9e7e86f (csv.test.ts BOM, delimiter, duplicates; Create those cohorts button) · CSV preview counts duplicate emails as importable; unmatched cohort imports with no cohort and nothing offers to create it; only a missing email column is detected (semicolons, BOM give a misleading message). csv.ts:105-160; BulkImportDialog.tsx:68-152
- **B-12** · ROUGH · fixed 9e7e86f (deleteLead test; Delete stays on every row, the prompt says Revoke applies once stations are sat) · Delete offered beside Revoke with no hint which applies until the 409. TraineesPanel.tsx:120-124
- **B-13** · ROUGH · partly fixed 9e7e86f (group delete disabled while it has members, cohort prompt says sittings detach; the count needs a cohort field on SittingRead) · Cohort delete does not say how many sittings detach (D9); group delete message only after the attempt. CohortEditDialogs.tsx:188; GroupEditDialogs.tsx:173
- **B-14** · ROUGH · partly fixed 9e7e86f (writes refetch only the lists they change; the first load still pages the whole roster, needs a count endpoint) · Roster pages the whole roster on every reload and refetches three lists per write. Roster.tsx:41-52
- **B-15** · ROUGH · open · Roster, sitting, circuit, rubric draft and exam edits carry no revision: last write wins. roster/router_admin.py:25-56; sittings/service_edit.py; catalog update_exam
- **B-16** · WRONG · open · StationTemplateEditScreen shows "Template not found" for any load failure. StationTemplateEditScreen.tsx:26-62
- **B-17** · ROUGH · open · listStationTemplates stops at 20 pages of 100 silently. authoring/api/templates.ts:56-80
- **B-18** · WRONG · open · Exam pickers (template wizard, create station, exams and programmes sections) ignore exams.error and rubrics.error: a failed load is an empty list. useAuthoringExamCatalog.ts:9-12; AuthoringExamSelect.tsx:25-39; ExamsSection.tsx; ProgrammesSection.tsx
- **B-19** · WRONG · open · Station create does not check the exam has a rubric; the station can sit in a circuit that later fails exam_rubric_not_ready. useCreateStationForm.ts:183-205
- **B-20** · WRONG · open · Publish and edit do no content validation server-side; a stale form can publish an empty station. stations/service_versions.py
- **B-21** · WRONG · open · Archive confirm says "removed from the live library"; _repoint_after_archiving may leave an older live version or retire the station. Delete of the only draft deletes the station without saying so. StationDetail.tsx; service_versions.py
- **B-22** · ROUGH · open · Station list pages oldest-first while copy says newest. stations/repository.py list_for_org
- **B-23** · ROUGH · open · Importer: upload errors through errorMessage only; needs a manual template publish hinted only by statusLine. ImportStationDialog.tsx:187-370
- **B-24** · WRONG · open · Exam edit: clearing the rubric sends null and the server drops None, so nothing changes. ExamFields.tsx; service_authoring.py update_exam
- **B-25** · ROUGH · open · Exam delete: ExamInUse shown raw with no pointer to Retire. service_authoring.py
- **B-26** · WRONG · open · RubricDetail shows Archive/Publish without owner_kind check (platform rubrics refuse); Publish on archived and Archive on drafts always fail. RubricDetail.tsx
- **B-27** · ROUGH · open · listProgrammes unpaginated; picker lists only published exams with no explanation. ProgrammesSection.tsx
- **B-28** · WRONG · fixed 53c86a8 (dashboard/support.test.ts: somebody who cannot author gets no setup guide) · Setup guide shown to supervisors with links to Build screens they cannot use. OrgDashboard.tsx; dashboard/support.ts
- **B-29** · ROUGH · open (design choice: Programmes and Stations are Build tabs, Team a People tab, Settings a staff capability; adding a nav entry for each needs a nav design decision) · Staff nav has no entry for Programmes, Stations, Library, Settings or Team; URL or Build only. surfaces/assess/surface.ts
- **B-30** · ROUGH · open · Generation routes are PlatformAdmin; the org "Generate with AI" tab answers locally. generation/router.py; useCreateStationForm.ts:135-148
- **B-31** · WRONG · open · SCIM token routes exist with no screen. roster/router_scim.py:56-90
- **B-32** · ROUGH · open · Resend invitation 429 and trainee_exists shown raw. router_admin.py:130-136; AddTraineePanel.tsx:60-70
- **B-33** · ROUGH · open · Org settings read-only, no SSO tab (U-17). OrgSettings.tsx
- **B-34** · ROUGH · open · "None" literal for cohort and programme in roster rows; "Exam type" survives in TemplateGenerationPanel; "Not live" pill on platform templates. roster/support.ts:21; TemplateGenerationPanel.tsx:94; StatusPills.tsx:36
- **B-35** · ROUGH · fixed bb24401 (cohorts created only when the import runs; Roster.tsx 131 lines) · Caused by 9e7e86f: a cohort created from the bulk import dialog stays behind when the import is cancelled; Roster.tsx is 333 lines against the 300-line warning. BulkImportDialog.tsx; Roster.tsx

## 3. Institution staff: run and assess (R-*)

- **R-7** · WRONG · fixed 1015ffb + e717819 · No delete, cancel or archive for a sitting or circuit; add-circuit and append-trainees have no guard after sign-off or release. sittings/router.py
- **R-8** · WRONG · fixed 80bfee0 (test_a_revoked_candidate_is_skipped_not_examined) · Revoked trainee still sits and is marked (checked only at build). sittings/service.py:125; service_structure.py:59,166
- **R-9** · WRONG · fixed 80bfee0 (test_only_the_named_supervisor_or_an_administrator_reviews_a_slot; test_an_observer_must_be_on_the_organisations_roster) · Any OrgStaff member can review any slot in the org; observer_trainee_id unvalidated. reviews/service.py:104
- **R-10** · WRONG · fixed 80bfee0 (test_a_circuit_review_is_finalised_once_and_only_in_its_own_organisation; ..._after_sign_off) · Circuit review finalize: no org check, no circuit_not_found, finalisable twice, no lock against sign-off. reviews/router.py
- **R-11** · WRONG · fixed 1015ffb · Decisions can be drafted for people who did not sit, and for training sittings. results/service.py save_draft
- **R-12** · WRONG · fixed 1015ffb · Redo of an earlier slot replays later stations; clear_patient marks an abandoned active slot COMPLETED. service_overrides.py; service_patient.py
- **R-13** · WRONG · fixed 1015ffb · End circuit with LiveKit down: error swallowed, circuit shows ended, agent may still be in the room. service_patient.py
- **R-14** · WRONG · fixed 1015ffb · clock_overdue raised with auto-advance off (false alert); copy says "check auto-advance". domain_alerts.py:21; sessions/support.ts
- **R-15** · WRONG · fixed 1015ffb · 12h stale auto-close ends paused circuits silently and marks unsat slots skipped. service_run.py:41; jobs.py:93
- **R-16** · WRONG · open · begin_consultation VoiceUnavailable leaves Reading with only the sweeper retrying; board shows clock_overdue not a voice fault. sittings/jobs.py; service_steps.py
- **R-17** · WRONG · open · No auto re-dispatch when the patient never arrives; manual resend only. domain_alerts.py; assessment session.py:87-99
- **R-18** · WRONG · open · useCircuitRun prefers a stale stream frame over a fresh fetch after an action; controls stay enabled while "Reconnecting". useCircuitRun.ts:~85-100; CircuitRunner.tsx:~95-101
- **R-19** · ROUGH/WRONG · open · End dialog records no reason; stale failure string reappears in the next dialog; override seconds NaN/0 sent unchecked; "stations can still be marked" shown to supervisors who cannot reach results; Edit offered to supervisors (rebuild is OrgAdmin). SupervisorControls.tsx; OverrideDialog.tsx; CircuitRunner.tsx:~85
- **R-20** · WRONG · open · /live: stream only with run_circuits so others see "Reconnecting" forever; "Open console" always opens circuits[0]; dead "deleted circuit" copy. LiveBoard.tsx
- **R-21** · WRONG · fixed 40b599b (support.test.ts in_progress is running) · SittingDetail report load .catch(() => null): 0 marked, 0 decided, no error; status badge treats only "live" as running (backend writes in_progress). SittingDetail.tsx:42,83
- **R-22** · WRONG · fixed 40b599b (sittingSteps.test.ts, three cases) · StepGuide: supervisors without sign_off_results see "Marking is not finished" forever; "Run" step has no link and false "start a new circuit" copy; Decide and Release shown for training sittings. sittingSteps.ts W (re-check: other session edits this file)
- **R-23** · WRONG · open · ReleaseAll drops candidates without trainee_id silently; remount in finally discards the "N released, M refused" alert; "Nobody has sat this yet" hides tiles while decisions exist. Results.tsx:~120-236
- **R-24** · WRONG · fixed 74bbded (test_a_withheld_or_inconclusive_outcome_is_not_released_or_emailed: 409 outcome_not_releasable, bulk skips it, no email) · Withheld or inconclusive outcomes are released and emailed "Your result is available". results/service.py:219-227; support.ts:38
- **R-25** · WRONG · fixed 74bbded (test_release_ignores_evidence_the_client_invents; evidence built server-side in results/service_evidence.py, the posted field is ignored) · Release evidence fingerprint is client-supplied. results/router.py:140-155
- **R-26** · WRONG · fixed 74bbded (web only: a 403 reading marks shows the slot review with a not-named notice; server access unchanged per R-9) · Unnamed OrgStaff reviewer gets a hard error reading marks on a slot they may review. service_access.py:48; SlotReview.tsx:62
- **R-27** · ROUGH · fixed 74bbded (supervisors get the candidate stepper; /report is OrgStaff) · SlotReview "Candidate N of M" reads the OrgAdmin report, so supervisors always see "Could not load the other candidates". SlotReview.tsx:118-120
- **R-28** · WRONG · fixed 53c86a8 (ForAdmins guard on schedule_sittings for newSitting, newCircuit, circuitEdit; no render test, node loader cannot render) · NewSitting/NewCircuit/EditCircuit reachable by supervisors with no can() guard: 403 on submit and loads; "group session" in subtitle. NewSitting.tsx; NewCircuit.tsx; EditCircuit.tsx
- **R-29** · ROUGH · fixed 53c86a8 (timing.test.ts: reading time held to 1-30, default 3) · Reading minutes: web allows 0, server clamps 1-30, defaults differ (2 vs 3). CircuitBuilder.tsx; timing.ts
- **R-30** · WRONG · partly fixed 53c86a8 (lock copy true, lead dropdown staff only; the lock is still read at load, a 409 on save is shown) · EditCircuit lock copy false once locked; lock read at load; lead dropdown lists admins who cannot run. EditCircuit.tsx
- **R-31** · WRONG · partly fixed 53c86a8 (note says filters cover loaded sittings only, no schedule prompt for supervisors; server-side filter needs an api change) · Sittings list filters and "Next up" operate on loaded pages only; "Schedule your first one" shown to supervisors. Sittings.tsx
- **R-32** · WRONG · open · Reporting route notFound for institutions; nothing aggregates across sittings or programmes. surfaces/assess/surface.ts; reporting/page.tsx
- **R-33** · ROUGH · open · Pass/fail wholly manual: no threshold proposal (D2); sign-off with pending reviews allowed (R-2 decided, attention step only). candidateProgress.ts:35
- **R-34** · ROUGH · open · Both review forms on one page; 2–3 release controls; late candidate (D7) and extra time (S-2) have no console control. slotReviewSteps.ts:66; DecisionParts.tsx
- **R-35** · ROUGH · open · Decision, review, sitting and circuit error codes shown raw (see section 11). CandidateDecision.tsx:140-146; SlotReview.tsx:214; AddTraineesDialog.tsx:215-221; GpLeadReview.tsx:131-135 (double message on conflict)
- **R-36** · WRONG · fixed 80bfee0 (test_a_training_review_is_shared_with_the_trainee_once_completed) · Training sittings: no share step; copy "once your supervisor shares it" false. MySittingDetail.tsx:116; reviews/service_summary.py:48. 
- **R-37** · ROUGH · fixed 74bbded (test_slot_review_failed_attempt.py: attempt_failed_reason on slot reviews; retry error shown once) · After a slot attempt fails with no_marking_rubric the slot review says nobody took the station, and a failed marking retry shows its error twice (marks form and marking panel). Caused by fix 1b2f457. results slot row has no attempt id for failed attempts; SlotReview.tsx
- **R-38** · WRONG · open · Not caused by a fix (found during 53c86a8): the api accepts any member, including a trainee, as a circuit's lead; only the web dropdown now filters. sittings/service_edit.py; CircuitBuilder.tsx (also 335 lines, over the 300-line warning)
- **R-39** · ROUGH · open · Caused by 74bbded: the candidate stepper lists the whole sitting, so a supervisor stepping to a slot they are not named on lands on the R-26 notice. SlotReview.tsx; CandidateStepper
- **R-40** · ROUGH · open · Not caused by a fix: sign-off copies the draft's evidence snapshot, so a station re-marked between draft and sign-off is refused evidence_changed only at release. results/service.py sign_off

## 4. Institution trainee (T-*)

- **T-3** · WRONG · open · Failed slot attempt has no record link (live_attempts_for_slots excludes failed); created/running attempt shows "being prepared" forever. attempts/repository.py:433; feedback/api.ts:63
- **T-4** · WRONG · open · Trainee in two orgs sees both orgs' sittings in either workspace. dashboard/service_trainee.py:30
- **T-5** · WRONG · open · No results or history entry: result reachable only via the sitting alert; self-practice attempts, transcripts and debriefs have no entry point; slot attempts get no debrief tutor. TraineeHome.tsx; service_debrief.py:32
- **T-6** · WRONG · open · MyReviewLink and MyResultLink use useAsync without a boundary: an error hides the link. MySittingDetail.tsx:214,241
- **T-7** · WRONG · open · JoinRoom: denied microphone only warns and joins; room and token errors raw. JoinRoom.tsx
- **T-8** · ROUGH · open · MyResult has no per-station breakdown and promises a notification; MyReview "Not ready yet" for any reason. MyResult.tsx; MyReview.tsx
- **T-9** · ROUGH · open · Finished sittings never leave the list; no past/upcoming grouping. TraineeHome.tsx
- **T-10** · ROUGH · open · Self practice empty state points to the library with no link; completeHref returns to the list not the feedback. SelfPractice.tsx

## 5. Consumer (C-*)

- **C-1** · WRONG · fixed 0dfc592 (markingWait.test.ts; an EvaluationFailed attempt still sits at interaction_complete until R-5 lands) · Marking wait never detects a failed attempt: "taking longer than usual" forever. markingWait.ts:45-51; MarkingModal.tsx:46,79
- **C-2** · WRONG · fixed 0dfc592 (startFailure.test.ts) · StationScreen attempt-creation error: raw message, no retry; station_not_published reads "A circuit can only use a published station". StationScreen.tsx:308-309
- **C-3** · WRONG · fixed b1b43bc (DebriefActions in AsyncBoundary; no render test, node runner has no JSX) · FeedbackStep hasFeedback has no boundary: failed load hides the debrief buttons. FeedbackStep.tsx:84-88
- **C-4** · WRONG · fixed 969f64b · Leaving mid-consultation ends the station, cannot resume; attempts created up front pile up as "Not started"; timers run from localStorage; stale sessionStorage attempt id reused on reopen. StationScreen.tsx; useStationAttempt.ts
- **C-5** · WRONG · fixed b1b43bc (model.test.ts nothingPickableMessage; test_entitlements_routes trial limits) · MockSetup with nothing pickable shows "An error occurred"; FREE_STATION_LIMIT hard-coded; 14-day expiry and 3-per-station cap not shown. MockSetup.tsx:22,100
- **C-6** · WRONG · fixed b1b43bc (model.test.ts describeCreateSetFailure) · CombineStations: every createSet failure is "Error creating mock" (incl. not_entitled, set_locked). CombineStations.tsx:118
- **C-7** · WRONG · fixed c2835df (attemptDestination.test.ts) · SetStation: unknown entry renders "station 1 of N" with null version; retired station no title or message; AttemptLanding reads page 1 of sets and can link /stations/null/practise. SetStation.tsx; AttemptLanding.tsx
- **C-8** · ROUGH/WRONG · fixed c2835df (dashboardView.test.ts nextStationCopy) · ExamDashboard hides RecentStations with 0 attempts in the current exam; NextStation hard-codes "Twelve minutes"; performance 404 swallowed as empty. ExamDashboard.tsx:84,139,157,226
- **C-9** · WRONG · fixed 04f288c (examSwitcher.test.ts offers a retry when exams could not be read) · useCurrentExam swallows a dashboard failure: exam switcher and exam-filtered nav vanish. useCurrentExam.ts:50,124
- **C-10** · WRONG · fixed c2835df (libraryPaging.test.ts libraryFailure) · Library loadMore failure clears the cursor; platform-leg 403 becomes an empty page with no paywall. useStationLibrary.ts:147; libraryPaging.ts:19,40
- **C-11** · WRONG · fixed c2835df (refusal.test.ts describeRefusal; DebriefSession and PeerPracticeProvider still word not_entitled themselves) · not_entitled carries the reason only in details; the web reads it nowhere, so lapsed vs exhausted vs expired cannot be told apart. entitlements/service.py:61
- **C-12** · WRONG · fixed 969f64b · MockEnd .catch to empty; media api, waitForDebrief, PendingFeedbackWatcher, help Messages swallow failures. MockEnd.tsx; waitForDebrief.ts:18; PendingFeedbackWatcher.tsx:61; help/Messages.tsx:59; media/api.ts:138,228
- **C-13** · ROUGH · fixed 04f288c (feedbackRows.test.ts) · Feedback history Evaluator hard-coded "system"; only first 25 attempts listed. FeedbackHistory.tsx:48; useStationAttempt.ts
- **C-14** · ROUGH · partly fixed 04f288c (registry.test.ts marketplace hidden for non-SCA; /app/me/stations redirects; reminder email link is E-3) · Marketplace reachable by URL for non-SCA exams; /app/me/stations is a 404 for consumers; reminder email links /marketplace for non-SCA. peer-practice/capability.ts; stations/capability.ts
- **C-15** · WRONG · open · Peer practice not on production; matcher pairs people for an exam with no published stations. BACKLOG
- **C-16** · ROUGH · fixed 04f288c (registry.test.ts transcripts and debriefs in the nav) · Transcripts and debriefs have no nav entry (links only). capability.ts hidden

## 6. Sign-in, account, billing, public (A-*)

- **A-4** · WRONG · fixed 1f7e50d · SAML failure redirects with error=sso_verification_failed but the page says "link is incomplete"; no RequireAnonymous so it overwrites a session; token stays in the URL; reload fails on the single-use token. SsoCallback.tsx; service_saml.py
- **A-5** · WRONG · fixed 1f7e50d · /login: readSsoSignIn swallows failures so sso_only members get a password form refused with password_login_disabled. account/api.ts; Login.tsx
- **A-6** · WRONG · fixed 68f967f (examSelection.test: ?appType seeds only when no exam is chosen) · /login?appType= overwrites the stored exam; Payments then lists the wrong plans and checkout refuses plan_not_available. Login.tsx land; useCurrentExam.ts
- **A-7** · ROUGH · fixed 68f967f (ssoCallback.test cancelled notice; RequireAnonymous follows a sanitised next) · RequireAnonymous drops ?next; sso_error notice never set. guards.tsx; authNotices.ts
- **A-8** · WRONG · fixed 1f7e50d · /register partial failure after the account exists says "couldn't create your account", retry says email_taken; unknown exam_code dropped silently. Register.tsx; identity/router.py
- **A-9** · ROUGH · fixed 68f967f (one-hour copy, SSO accounts mentioned, 30 s resend cooldown; no unit test for the cooldown) · /forgot-password copy "expires shortly" (60 min), SSO-only accounts get "on its way" with no email, no resend cooldown. ForgotPassword.tsx
- **A-10** · WRONG · fixed 1f7e50d · /reset-password does not clear the local session; /login then bounces to /app where everything 401s. ResetPassword.tsx; guards.tsx
- **A-11** · ROUGH · fixed 68f967f (second_step and sign_in_failed wording; empty token links to sign in) · /accept-invitation: failed login or MFA after setting the password shows only "Your account is ready"; empty token offers forgot-password. ResetPassword.tsx
- **A-12** · ROUGH · fixed 68f967f (validateAuthForm.test: two-class rule matches the server) · Password hint says 12 characters; server also needs two classes (weak_password after submit). ResetPassword.tsx; Register.tsx
- **A-13** · WRONG · fixed 1f7e50d · Change password says "use it next time" but revokes every chain including the current one: signed out ~15 min later unwarned; no RequireSession on the page; accounts with no hash (SSO, never-accepted) can never pass "current password". ChangePasswordRequired.tsx; settings/ChangePassword.tsx
- **A-14** · WRONG · open · Refresh 503 becomes a sign-out while cookies are valid; no global 401 handler so a revoked session shows per-screen errors; /app spinner with no error path for a stale lastWorkspace; no server-side session gate; CSP report-only unless env set. SessionProvider.tsx; client.ts; app/page.tsx; middleware.ts
- **A-15** · WRONG · open · /billing/complete ignores session_id, polls 6×2s swallowing every error incl. 401, says "Payment received" with no sign-in prompt; "You're all set" immediately for anyone holding a live entitlement (renewals, trial rows). PaymentReturn.tsx:60
- **A-16** · WRONG · open · PlanPicker handles only two referral codes; plans filtered by localStorage exam; "50/100/150 stations" blurbs conflict with /pricing (75/100) and the API; referral price shown whenever a code is typed. PlanPicker.tsx
- **A-17** · WRONG · open · POST /billing/checkout: no existing-entitlement check (double purchase); Idempotency-Key read by no route. billing/router.py; client.ts
- **A-18** · ROUGH · open · PaymentsPanel fetches receipts one by one under Promise.all (one bad receipt fails the panel), ignores next_cursor; trial row under "Receipts"; window.open after await popup-blocked. PaymentsPanel.tsx; ReceiptList.tsx
- **A-19** · WRONG · open · /pricing prices and counts hard-coded (PLAB "75" vs "100+"); landing section disappears when an exam has no plans; cancelled checkout has no route back to buy. Pricing.tsx
- **A-20** · ROUGH · open · /exams/classic and /exams/avodeck not in the rewrite list or EXAMS; compliance pages dated January 2025 with two contact emails; landing stats swallow errors.
- **A-21** · WRONG · open · Referrals tab adminOnly while checkout, T&Cs and POST /me/referral-code exist for everyone; ?tab=referrals falls back silently; ReferralDetail shows the viewer's exam not the referee's; "within 48 hours" unverifiable. Settings.tsx; ReferralDetail.tsx; ReferralsInfo.tsx
- **A-22** · WRONG · open · CloseAccount says it permanently removes attempts and ends subscriptions; the API only sets deleted and clears the password, erasure runs 30 days later; sign-in afterwards says account_suspended. CloseAccount.tsx; router_me.py /me/close
- **A-23** · WRONG · open · ProfilePanel invents "SCA" for users with no exam; ExamPanel "Failed to update" for every code; avatar errors raw. ProfilePanel.tsx; ExamPanel.tsx

## 7. Platform staff console (P-*)

- **P-12** · WRONG · open · Pilot settings save always sends reset_spend_alerts=true. pilotForm.ts
- **P-13** · WRONG · open · Revenue-by-plan section failure={() => null}. BmjDashboard.tsx
- **P-14** · ROUGH · open · isPartnerAddress hard-codes @{partner}.com. ReportersPanel.tsx
- **P-15** · WRONG · open · Referral payouts: limit 100, next_cursor ignored, totals undercount, no confirm on Paid. ReferralPayouts.tsx
- **P-16** · WRONG · fixed 969f64b · Moderation: API caps at 100 with next_cursor None, hero says "100 posts"; no author, report count or link. router_platform.py:22-36; ModerationHome.tsx
- **P-17** · WRONG · partly fixed 969f64b (reason text needs a column) · Station flags: limit 100 no LoadMore; no reason text or station link. platform/api.ts:449-457; StationFlags.tsx
- **P-18** · WRONG · open · Audit (global 100, org 50) no cursor use. PlatformAudit.tsx; AuditSection.tsx
- **P-19** · ROUGH · partly fixed 969f64b · Media hand-check route has no caller; detail load error has no retry; production errors raw. media_production/router.py; MediaDetailScreen.tsx
- **P-20** · ROUGH · open · Ops live badge "Reconnecting" with stale data and no timestamp. Ops.tsx
- **P-21** · WRONG · open · "SSO only" hides the password form with no check against password-seated members. SsoSection.tsx; sso/service.py:109
- **P-22** · WRONG · open · Org Members limit 50 ignores cursor; "Nobody has joined" when only trainees exist; no resend or temp-password status. MembersSection.tsx
- **P-23** · WRONG · open · org_slug_taken shown as top alert; org_type change leaves misfit roles; Overview copy "Every organisation is active or on trial" false; at-risk list unpaged. ProvisionPanel.tsx; OrganizationSettings.tsx; Overview.tsx
- **P-24** · WRONG · open · Invite platform admin email-only, invitee name set to email. InvitePlatformAdminModal.tsx
- **P-25** · WRONG · open · Users: failed facts/plans loads look empty; memberships panel shows raw role and no org name; "invited" never shows; Deactivate leaves running attempts and roles, deactivated sole admin still counts. Users.tsx; AccountTab.tsx; service_memberships.py
- **P-26** · WRONG · open · "Password reset emailed" toast regardless of delivery. ProfileTab.tsx
- **P-27** · WRONG · open · Attempt inspector Salvage/Fail with no staleness check (a live consultation can be failed); no sitting context for exam_slot. AttemptInspector.tsx
- **P-28** · WRONG · open · Billing tab: "£12" becomes NaN then null, plan price recorded silently; retired plan offered; Record refund on refunded payments, refund does not touch Stripe; unprocessed event with no failure is "Pending" with no retry and excluded from failed_only; per-user lists unpaged; extend date unchecked. BillingTab.tsx; Payments.tsx; BillingEvents.tsx

## 8. Hire and partner (H-*, F-*)

- **H-3** · WRONG · open · Hire: no "My training" nav so candidates reach results only by email; /live, /trainees, /team, /mocks unlinked; ProvisionPanel hint contradicts the Employer option. surfaces/hire/surface.ts
- **H-4** · WRONG · open · Partner: every route but dashboard, reporting, team is notFound; signups chart, byExam and fee banner failure={() => null}; "Add reporter" platform-admin only; no reporter list or revoke UI; date-range codes raw; consumer Settings tabs shown; "Build" nav shown to partner_admin. partner/Dashboard.tsx; Reporting.tsx; authoring/capability.ts
- **F-3** · ROUGH · open · Screen does not consult manifest.screenNames (drift possible); staffHiddenOn pages stay reachable by URL; /circuits/[id]/edit, /mocks/list, /slots/[id]/review, /shared-reviews/[id] linked from nowhere. screen.tsx; registry.ts

## 9. State over time and scale (S-*)

- **S-10** · WRONG · open · Lapsed subscriber past day 14 is told trial_exhausted (expired never reached); invited account's trial counts from created_at; failed/abandoned set station burns a trial station. entitlements/domain.py; attempts/domain.py
- **S-11** · WRONG · open · Entitlement check only at attempt creation: expiry or revocation mid-attempt ignored; unstarted-attempt resume runs before require. attempts/service.py
- **S-12** · ROUGH · open · Renewal overlaps instead of extending; no expiry-warning job or email. billing/service_settlement.py
- **S-13** · WRONG · open · Only checkout.session.completed acted on: refunds and disputes leave access; no referral clawback. billing/domain.py
- **S-14** · WRONG · open · Org entitlement grant/revoke, set_access, SCIM, exam retire/delete, station archive/delete, rubric publish, sitting/circuit end, trainee delete, account close and erasure write no audit row. (services listed in sweep G)
- **S-15** · WRONG · open · Org practice-access grant never expires and ignores org suspension; a lapsed grant is reported as "revoked". service_practice_access.py
- **S-16** · WRONG · open · Contract end suspends with audit only, no email; restore and update_organization do not clear or honour contract_ends_at; nothing ends a trial; no org deletion; inactive/churned statuses all blocked. tenancy/jobs.py; service_platform.py
- **S-17** · WRONG · open · Suspended org: login succeeds then every org route 403s unhandled (F-1); the worker keeps advancing circuits; SCIM events refused and lost. core/tenancy.py; service_run.py; service_scim.py
- **S-18** · WRONG · open · SCIM deprovision revokes membership only (slots, attempts continue), trainees only, no audit. service_scim.py
- **S-19** · WRONG · open · Close account: cannot reopen despite the "month to change their mind" docstring; no audit or email; memberships, slots and live attempts untouched; email taken 30 days; add_membership can attach to a closed account; closed sole admin not guarded. service_close_account.py; service_memberships.py
- **S-20** · WRONG · open · Erasure: transcripts and marks gone but decisions remain; one exception aborts the batch. service_erasure.py
- **S-21** · WRONG · open · Anonymise: PDF, CSV, report and cohort still show the real name and email; account, transcripts untouched; live slots continue; freed email re-rosters as a new trainee. service_result_pdf.py _candidate_name; service_report.py:86-87; service_cohort.py:71-72; service_report_csv.py:102-103; roster/service_edit.py
- **S-22** · WRONG · open · Role change or removal applies at next token (up to 15 min), SSE not closed; demoted or removed supervisor keeps leading a circuit. core/tenancy.py; service_memberships.py
- **S-23** · WRONG · open · No self-serve email change; roster and account emails diverge (roster link, Stripe match, trainee_email).
- **S-24** · WRONG · open · create_sitting checks neither exam nor programme status; set_programme_status enforced nowhere; retire_exam does not cascade. sittings/service.py; catalog/service_programmes.py
- **S-25** · WRONG · open · Stalled job requeued once then failed silently; consumer attempt stuck in created/running has no reaper; sweep failures logged only; paused circuit force-ended at 12h; outbox drains 20 per run (500 invites ≈ 25 min); erasure batch aborts on one error. health/service.py; sittings/jobs.py; notifications
- **S-26** · WRONG · open · Bulk import, single adds and resends share OUTBOUND_EMAIL 30/h per user: more than 30 resends in an hour 429s; rate limits handled only in MFA/2FA/help panels; retry_after never read. core/rate_limit.py
- **S-27** · WRONG · open · collectPages stops at 25 pages silently; programmes, cohorts, groups lists first page only; SSE has no connection cap and auth is checked once at open. domains/assess/api.ts; core/sse.py

## 10. Emails (E-*)

- **E-1** · WRONG · open · No template or enqueue exists for: exam-day, sitting scheduled, review assigned, release to institution staff, invitation reminder, referral redemption, erasure/anonymise confirmation, entitlement expiry, org contract end. notifications/service.py _TEMPLATES (11 keys)
- **E-2** · WRONG · open · payment_receipt says "open the full receipt in your account" with no URL; only an oracle unit test. billing/service_settlement.py:99-103
- **E-3** · WRONG · open · marketplace_session_reminder links /marketplace (legacy redirect only) with a raw ISO UTC time. service_reminders.py:48-52
- **E-4** · WRONG · open · Unknown template key sends a debug-style email instead of failing. notifications/service.py _render
- **E-5** · ROUGH · open · Invitation and practice-access invitation: 7-day TTL, no reminder; practice_access_granted links /login not the practice area; inactive_user_engagement daily with no cap via a legacy redirect. identity/service_invitations.py; service_engagement.py
- **E-6** · ROUGH · open · Abuse and no-show reports use uuid4 idempotency keys (never deduplicated); partner_spend_alert falls back to support so the partner never sees it. service_reports.py; service_spend.py
- **E-7** · WRONG · open · Delivery: 6 attempts then abandoned, nothing surfaces it (S-5); Resend domain unverified on staging (B-1).

## 11. Error codes with no web handler

- **identity**: `account_suspended`, `password_login_disabled`, `invalid_legacy_token`, `legacy_account_not_imported`, `legacy_exchange_unavailable`, `invalid_refresh_token`, `too_many_requests`, `invalid_input`, `user_not_found`
- **mfa**: `invalid_mfa_code`, `mfa_challenge_expired`, `mfa_not_enrolled`, `mfa_already_enrolled`, `mfa_required_by_policy`
- **profile**: `exam_already_chosen`, `unknown_exam`, `invalid_avatar_file`
- **billing**: `plan_not_available`, `checkout_failed`, `receipt_not_found`, `unauthenticated`, `price_creation_failed`, `plan_not_found`, `plan_code_taken`, `unknown_plan`, `payment_not_found`, `payment_already_recorded`, `invoice_*`, `invalid_invoice_line`, `invalid_signature`, `invalid_webhook`, `billing_event_not_found`, `entitlement_not_found`, `practice_access_exists`
- **sso**: `sso_not_configured`, `sso_provider_unsupported`, `sso_login_unavailable`, `unknown_sso_provider`, `sso_verification_failed`, `invalid_sso_binding`, `saml_connection_not_found`, `sso_binding_taken`, `sso_not_configurable`, `invalid_saml_connection`
- **growth**: `unknown_partner`, `payout_account_number_required`, `referral_not_found`, `referral_not_redeemed`, `reporter_not_found`, `invalid_date_range`, `invalid_bucket`, `exam_not_in_pilot`, `not_a_partner_reporter`, `referral_code_taken`
- **public_site**: `invalid_message`, `message_not_found`, `announcement_not_found`, `inbox_message_not_found`, `message_not_repliable`
- **catalog**: `exam_code_taken`, `exam_already_imported`, `exam_not_publishable`, `invalid_exam_code`, `invalid_exam_settings`, `ExamInUse`, `unknown_exam`
- **stations**: `not_editable`, `fact_check_running`, `station_being_produced`, `not_deletable`, `draft_exists`, `already_published`, `not_archivable`, `station_not_published`, `template_not_published`, `version_not_found`, `station_not_found`, `station_flag_not_found`, `station_template_not_found`, `station_template_version_not_found`, `generation_profile_not_found`, `invalid_photo`, `not_a_media_block`, `photo_not_on_station`, `photo_storage_unavailable`, `invalid_import_file`, `station_import_not_found`, `import_not_ready`
- **roster**: `trainee_exists`, `cohort_exists`, `cohort_not_found`, `group_exists`, `group_not_found`, `trainee_not_found`, `trainee_revoked`, `trainee_not_on_roster`
- **entitlements**: `practice_access_exists`, `entitlement_not_found`, `invalid_email`, `not_entitled` (except library paging), `grantee_not_found`
- **scim**: `scim_invalid_filter`, `scim_invalid_value`, `scim_mutability`, `scim_not_found`, `scim_token_not_found`, `scim_unauthorized`, `scim_uniqueness`
- **sittings**: `circuit_not_found`, `circuit_not_live`, `circuit_not_started`, `circuit_paused`, `circuit_not_paused`, `circuit_already_ended`, `no_active_station`, `sitting_not_found`, `slot_not_found`, `programme_required`, `programme_exists`, `rubric_not_found`, `rubric_version_not_found`, `circuit_locked`, `invalid_circuit`
- **reviews**: `result_not_released`, `not_signable`, `incompatible_outcomes`, `recruitment_outside_exam`, `review_incomplete`, `nothing_to_review`, `invalid_review_status`, `invalid_rating`, `review_conflict`
- **results**: `result_not_released`, `not_signable`, `incompatible_outcomes`, `recruitment_outside_exam`, `invalid_workflow`, `evidence_changed`
- **voice** / **assistant**: `assistant_session_not_found`, `assistant_session_not_joinable`, `assistant_session_not_ready`, `assistant_session_not_yours`, `unknown_assistant_type`, `knowledge_unavailable`, `tool_arguments_invalid`, `unknown_tool`, `tutor_note_not_found`, `debrief_not_found`, `voice_unavailable`, `attempt_not_joinable`, `attempt_not_ready`, `attempt_mismatch`, `invalid_attempt_state`
- **attempts**: `attempt_not_found`, (others listed with voice/assistant and sittings)
- **station_sets**: `set_not_found`, `set_entry_not_found`, `set_locked`, `set_has_attempts`, `set_entry_has_attempts`, `station_version_not_usable`, `attempt_limit_reached`, `nothing_to_debrief`
- **media**: `media_not_found`, `unknown_media_kind`, `empty_query`, `media_being_produced`, `item_not_found`, `wrong_media_kind`, `av_already_running`, `av_unavailable`, `script_not_checked`, `claim_outside_item`, `not_editable`, `fact_check_running`, `station_being_produced`, `slug_taken`, `unusable_title`, `station_has_no_template`, `invalid_media_status`
- **community**: `post_not_found`, `post_not_yours`, `invalid_author_filter`, `empty_content`, `content_too_long`, `tag_too_long`, `too_many_tags`, `post_unavailable`, `cannot_claim_own_post`, `not_your_post`
- **marketplace**: `post_not_found`, `post_unavailable`, `slot_already_claimed`, `cannot_claim_own_post`, `not_your_post`, `peer_session_not_found`, `peer_session_not_open`, `too_early_to_join`, `unknown_exam`
- **peer_practice**: `queue_entry_not_found`, `practice_session_not_found`, `already_queued`, `practice_session_ended`, `practice_session_not_accepted`, `practice_feedback_not_open`, `partner_unavailable`, `unknown_exam`
- **tutor_memory**: `debrief_not_found`, `note_not_found`
- **cv**: `invalid_cv_file`, `cv_not_found`
- **tenancy**: `org_not_found`, `not_a_member`, `membership_not_found`, `platform_admin_exists`, `org_slug_taken`, `membership_exists`, `weak_password`, `last_admin`, `invitation_not_pending`, `organization_suspended`, `mfa_not_enrolled`
- **rubrics**: `rubric_not_found`, `rubric_version_not_found`, `invalid_rubric`, `already_published`, `not_archivable`
- Unknown codes fall through to the server's English message; `retry_after` is never read by the web; the generated union omits `announcement_not_found`, `inbox_message_not_found`, `message_not_repliable`; a doc comment cites `trial_exhausted`, which does not exist.

## 12. Not provable from code: the staging run

Live consultation end to end; a real scoring run and the score and priority columns; result and invitation email delivery; debrief clock (V-1/V-2); erasure and export on production (E-3); whether the voice token mint re-checks entitlement; the assessment worker's behaviour mid-attempt on org suspension; Entra state echo; Stripe session_id vs webhook wording; referral payout timing; CSP enforce in production; SSE behaviour with 50 viewers.

## 13. Fixed since the 2026-10-06 walkthrough

| Item | Status | Note |
|---|---|---|
| B1 | Fixed | Circuit builder, org stations: the platform leg is skipped for org-owned exams |
| B2 | Fixed | Roster add gives no membership: membership is granted on add, restored on restore, and granted on claim |
| B3 | Fixed | Accept-invitation hydration: submit is disabled until hydrated |
| B4 | Fixed | Trainee sees staff reads: staff routes are OrgStaff or OrgAdmin |
| B5 | Fixed | Draft exams hidden: lists all statuses, with a "Drafts only" checkbox |
| B6 | Partly | "No template" dead end: save is blocked, and there is a link to create a template |
| B7 | Fixed | Admin 403 on slot review: only a 404 means "no marking yet", other errors show a retry |
| B8 | Fixed | /app landing: order is last workspace, then first institution, then personal |
| B9 | Partly | "None" labels, CSV name: the CSV name column is fixed, but a literal "None" still shows for cohort and programme |
| B10 | Fixed | Retire on platform exams: platform exams are locked, Retire shows only for published, unlocked exams |
| B11 | Fixed | Programme exam-code free box: a Select of published exams, with a hint |
| B12 | Partly | Platform exams in the circuit builder: see gap B-2 (platform leg needs personal entitlements) |
| B13 | Fixed | Results counts: tiles show Undecided and Awaiting marking |
| B14 | Fixed | Live board errors: shows an alert and stops retrying on 401/403 |
| B15 | Partly | Supervisor 403 buttons: sitting, sign-off and team controls are gated, but authoring buttons in ExamsSection and ProgrammesSection are not |
| B16 | Partly | Settings Save and SSO: the dead Save is gone, the Organisation tab is read-only, and SSO shows only a paragraph and the staff-MFA rule |
| B17 | Fixed | Rubric double-create: holdOnSuccess plus disabled while busy |
| B18 | Fixed | Runner shows no supervisor: falls back to the email, otherwise "No supervisor assigned" |
| B19 | Fixed | Not assessed and priority: shows "No automatic score" or "Not assessed", priority is standard when there is no score |
| B20 | Fixed | Result email link: links to /app/{org}/trainee/results/{sitting} and names the institution |
| Confusion 1 | Fixed | Setup order: eight steps in build order |
| Confusion 2 | Partly | Nav clutter: media, debrief and transcripts have no staffHiddenOn, not verified |
| Confusion 3 | Partly | Two review forms: one form is open and the other is folded, but both are on the page |
| Confusion 4 | Partly | Undecided and score column: Undecided tile added, a score column needs a staging walk |
| Confusion 5 | Partly | Release controls: there are still 2 or 3 controls, but the confirmation modal exists |
| Confusion 6 | Fixed | Sign-off with incomplete reviews: R-2 decided, candidateProgress.ts shows "Reviews not complete" as an attention step |
| Confusion 7 | Partly | Role vocabulary: one vocabulary, but there is no examiner role |
| Confusion 8 | Partly | Template wizard steps: "Exam type" survives in TemplateGenerationPanel.tsx |
| Confusion 9 | Partly | Template "Not live" and New draft: hidden for platform templates, but the "Not live" pill remains at StatusPills.tsx |
| Confusion 10 | Fixed | Rubric versions: ExamFields.tsx shows the latest published version only |
| Confusion 11 | Fixed | Programmes nav: a build-order tab list |
| Confusion 12 | Fixed | Empty-state wording: covered by the AsyncBoundary changes |
| Confusion 13 | Fixed | Supervisor "Nothing assigned": SupervisorCircuits.tsx; OrgDashboard.tsx sayWhenEmpty={!admin} |
| Confusion 14 | Partly | Revoke/Delete/Anonymise unexplained: TraineeRowActions.tsx now has tooltips, traineeStatus shows a stage, "Exam access" is still a separate tab |
| Confusion 15 | Fixed | Platform org creation: Organizations.tsx navigates to ?tab=members |
| Confusion 16 | Fixed | Accept to workspace: ResetPassword.tsx signInAfterInvitation |
| Confusion 17 | Partly | Self practice opens an attempt immediately: SelfPracticeStation.tsx changed in a6e37f1, probably partly addressed |
| 2026-10-07 | content r5 | 969f64b + 0d49c18 (review) | P-4 P-16 C-4 C-12 fixed; P-17 P-19 partly | P-17 reason needs a StationFlag column (migration) |
| 2026-10-07 | access r2 | 1f7e50d | S-5 A-4 A-5 A-8 A-10 A-13 fixed; 9593584 review folded in | none |
| 2026-10-07 | institution r4 | 1015ffb | R-11..R-15 fixed, R-7 api only; setup-step flake fixed; 80bfee0 review folded in | R-7 web buttons |
| 2026-10-08 | marking r1 | R-5, S-2, S-8 fixed 1b2f457 (retry with backoff, marking_failed flag, staff retry route, slot refused when unmarkable) | none in batch; types hand-declared until regenerated |
| 2026-10-08 | institution r5 | R-7 web cancel/delete fixed e717819; 1015ffb review folded in (rewrap reverted, NotDecidable base, ensure_sitting_open, CLEAR_ROOM_RETRY) | order-dependent log-capture flake in test_circuit_run (structlog cache) noted |
| 2026-10-08 | night r1 (access, institution, marking) | B-1 P-1 P-8 (610efab); P-6, H-1 partly (c3983f0); P-2 P-3 P-7 (a451a1e) | S-7 needs a design choice; openapi regen blocked by the user's dirty openapi.json |
| 2026-10-08 | night r1 institution | B-9 B-11 B-12 fixed, B-13 B-14 partly (9e7e86f); review fixes 85c0f5b (c3983f0), 23f925e (a451a1e), b6ee5ea (610efab) | B-10 stays by design; B-35 new (caused by 9e7e86f) |
| 2026-10-08 | night r1 access | SSO takeover closed e92016f (+b6ee5ea, f354e1c review fixes); P-5 fixed, P-10 P-11 fixed under P-9 (c6bbf14) | H-2 needs a product decision; P-9 reply UI is the user's inbox work |
| 2026-10-08 | night r1 institution | review fixes bb24401 (9e7e86f, 85c0f5b; B-35 fixed there); B-28 R-28 R-29 fixed, R-30 R-31 partly (53c86a8) | B-29 needs a nav decision; R-38 new |
| 2026-10-08 | night r1 access | A-6 A-7 A-9 A-11 A-12 (68f967f); SSO review fixes a59e4d6 (second provider keeps the chosen password, TOTP cleared, SAML save audited) | an own-password account linking SSO for the first time after a relayed seat still loses its password (audit cannot tell; reset recovers) |
| 2026-10-08 | night r1 marking | R-24 R-25 R-26 R-27 R-37 (74bbded); review fixes 6425e2b (23f925e) | R-39 new (caused by 74bbded), R-40 new; openapi needs attempt_failed_reason and outcome_not_releasable |
