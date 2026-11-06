# Institution overhaul browser verification (main tree, local api :8002, web :3100)

Worlds: e2e world (org e2e-mw3om0c6, hire e2e-hire-mw3om0c6) and a fresh empty org (ov-fresh). Completed slots were seeded by psql (no LiveKit locally). Screenshots and .aria.txt snapshots sit beside this file. Console and network problems were recorded per page; "none" means zero 4xx/5xx and zero console errors.

| Screen | Role | Result | Symptom | Screenshot |
|---|---|---|---|---|
| Home setup assistant steps 1-5 | admin (fresh org) | pass | none | home-setup-assistant-step1..5.png |
| Home / Today | admin | pass | none | admin-home.png |
| Exams hub: Exams, Stations, Marking schemes, Station layouts, Programmes | admin | pass | none | exams-hub-*.png, admin-exams.png |
| New exam sheet, direct URL /authoring/exams/new | admin | FAIL | main renders blank: useExam(null) is empty and AsyncBoundary has no `empty` prop (NewExamSheet.tsx) | exams-new-exam.png |
| New exam sheet via ?exam=<id>, steps to publish | admin | pass | reaches "Available for scheduling" | exams-new-exam-step2..4.png, exams-new-exam-resume.png |
| Exam detail, settings | admin | pass | none | exam-detail-available.png, exam-settings.png |
| Adopt an OSCE Guide exam | admin | pass | none | adopt-exam-dialog.png |
| New station chooser, create blank | admin | pass | none | station-new-chooser.png, station-create-blank.png |
| Marking scheme builder, versions | admin | pass | none | scheme-builder-new.png, scheme-versions.png |
| Station layout new | admin | pass | none | layout-new.png |
| Schedule a sitting wizard (formal) steps 1-6, created | admin | pass | none | schedule-wizard-*.png |
| Sitting page and tabs | admin | pass | none | sitting-page.png, sitting-tab-*.png |
| Circuit edit / new | admin | pass | none | circuit-edit.png, circuit-new.png |
| Console before start, running, end confirm | admin | pass | none | circuit-console-*.png, circuit-end-confirm.png |
| Live board idle and running | admin | pass | none | live-board-*.png |
| People: trainees, staff, groups, exam access, history, add sheets, bulk revoke | admin | pass | none | people-*.png |
| Results index (needs decision) | admin | pass | none | results-index.png, results-index-w2.png |
| Sitting results: undecided, released, training | admin | pass | none | sitting-results-*.png |
| Circuit review after end | admin | pass | none | circuit-review-after-end.png |
| Circuit review, marked fixture | admin | FAIL (possible fixture artefact) | circuit page says "Mark each station 0 of 1 marked / Marked on 0 of 1 station" while sitting results says "Mark 1 of 1 marked" for the same sitting; the seeded result has no admin review | circuit-review-marked.png |
| Slot review (exam, training) | admin | pass | none | slot-review-exam.png, slot-review-training.png |
| Settings, Invoices, Reporting | admin | pass | none | settings.png, invoices.png, reporting.png |
| Supervisor home | supervisor | pass | none | supervisor-home.png |
| Supervisor slot review | supervisor | pass | none | supervisor-slot-review.png |
| Trainee home (running) | trainee | pass | mic-blocked alert is the headless browser | trainee-home*.png |
| Trainee sitting, FINISHED exam and practice | trainee | FAIL | still shows "Check your microphone" and (exam) "Before you start: your station opens when your supervisor starts it" after the sitting is completed | trainee-sitting.png, trainee-training-sitting.png |
| Trainee result released; undecided | trainee | pass | none | trainee-result*.png, trainee-undecided-result.png |
| Trainee station review | trainee | pass | "Not rated" is the seeded fixture | trainee-review.png |
| Trainee self practice | trainee | pass | "No published stations yet" in the e2e org | trainee-practice.png |
| Hire home (Setup, At a glance) | hire admin | pass | none | hire-home.png |
| Hire Assessments, schedule an assessment | hire admin | pass | empty states correct | hire-assessments.png, hire-schedule.png |
| Hire Candidates | hire admin | FAIL | employer page uses institution wording: "Candidates sit sittings", "exam or training circuit" | hire-candidates.png |
| Candidate brief opens when the circuit starts | trainee | not testable | no LiveKit locally ("Patient Biodata" never renders) | trainee-home-running.png |

Not walked: Staff spreadsheet import flow; schedule wizard training retry path.

## npm run e2e:assess

6 passed, 2 failed, 1 did not run.
- ASSESS-1 FAIL: web/e2e/assess/build-sitting.spec.ts:14 expects "Everything is in place. Schedule the first sitting." which the UI no longer shows (stale expectation).
- ASSESS-2 FAIL: run-circuit.spec.ts:45 brief never opens; no LiveKit locally, same as baseline.
- ASSESS-3 did not run (depends on ASSESS-2).

## Round 2 (2026-11-05)

Browser walk, Chrome via the web `verify` harness, desktop 1366x900 and mobile 390x844, no source edited. Evidence: `r2-*.png`, `r2-*.aria.txt`, `r2-log.jsonl` (263 visits) in this folder.

| Screen | Role | Result | Note |
|---|---|---|---|
| Home / Today (idle, running, ended) | admin | pass with nit | "Your next circuit" still says "The console opens when the sitting starts." while running (r2-admin-run-home-d.png); chip reads "In progress" |
| Exams hub: exams, stations, layouts, schemes, programmes | admin | pass with leaks | layouts called "Station layouts" and "Station templates" in different places |
| Exam detail, settings, new exam wizard | admin | pass | publish step not reached (wizard resume) |
| New / create / import station, layout builder, scheme + versions | admin | pass | scheme shows Shown/Hidden chips |
| People, add people, staff + trainee import | admin | pass with nit | import dialog button stays "Cancel" after import; "Cohort" label in trainee edit |
| Trainee detail | admin | pass | |
| Sittings, wizard (formal + training), circuit failure retry | admin | pass | both retry paths show "The circuits were not made" + Try again |
| Sitting page, edit circuit, console, live board (running, ended) | admin | pass with nits | ended console says "1 of 1 stations sat" for a never-sat station; edit circuit shows the design note "Used for Edit on an existing circuit..." |
| Results, sitting results, circuit/slot review, Reporting, Settings, Invoices | admin | pass | |
| Supervisor home, circuit run | supervisor | pass with errors | 2 console 403s on circuit-run page |
| Trainee home, sitting, result, review, self practice | trainee | pass | |
| Hire home, Assessments, schedule, Results | hire admin | pass with leaks | /team h1 "Candidates" ok; Exams hub shows sitting/trainee words |
| Hire home, results, practice | hire candidate | FAIL | "Self practice / From your organisation" card shown to a hire candidate; Results h1 "Assessment outcome" |
| Hire Candidates dialogs (edit, delete, add) | hire admin | not reached | e2e org had zero candidates; page loaded, dialogs not opened |
| Partner home | partner | pass | |
| /sign-in, /invitations/accept | anon | 404 | real routes are /login, /accept-invitation |
| 390px overflow | all | none found | |

### e2e (web/, Playwright, assess + hire + partner + roles)

17 passed, 9 failed, 1 did not run. Failures: board-home x4 (desktop, mobile, computed styles, hover), ASSESS-2 (no LiveKit, expected), ROLES-1 consumer and platform admin, SWITCH-1, SWITCH-2. ASSESS-3 did not run. employer.spec.ts and partner.spec.ts passed.
