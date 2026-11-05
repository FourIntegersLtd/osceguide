---
paths:
  - "api/app/features/{sittings,roster,dashboard}/**"
  - "api/tests/e2e/**"
  - "web/src/domains/assess/**"
  - "web/src/surfaces/{assess,hire}/**"
  - "web/e2e/assess/**"
---
# Exam day: what to know

Owner: `institution-owner`. Proof: `verify-institution` (clock and rooms also
`verify-attempt-engine`). Hire is exam mode: a GP lead is an org admin reviewing exam-mode
sessions, not a separate product. B2B defines its own exams and never waits on the platform
catalogue (ADR 0017); do not build against an open decision in `web/docs/BACKLOG.md` (D7-D10).

- **The circuit runs itself** (ADR 0018). The server owns the clock: read `remaining_seconds` and
  `phase_ends_at`; never run an authoritative countdown in the browser.
- The patient is dispatched on the server's clock when reading ends; if nobody joined the room
  during reading, the circuit sits overdue for ever. Starting the room is `attempt-engine-owner`'s.
- **`trainee_id` means two things.** Circuit slots use `users.id`; result decisions use `trainees.id`.
- A slot's attempt must be `kind = 'exam_slot'` (`kind_matches_reference`). To put marked work in
  front of an examiner locally, copy a marked attempt as an exam-slot attempt:
  `web/.claude/skills/verify/features/feedback-fixture.sql`.
- Deactivating a trainee cleans their slots; a sole admin cannot be locked out; a stale revision
  is refused (`stale_revision`); a cancelled or edited sitting notifies (`sitting_emails`).
- Dashboard read models: `service_org`, `service_live`, `service_readout`, `service_report*`,
  `service_trainee`. The learner's own home, performance and achievements files are
  `web-foundation-owner`'s; the staff console's are `staff-console-owner`'s.
- A review screen renders for a slot with no attempt; a local DB has exams and rubrics but often no
  stations or marked attempts (`features/rubric-builder.md` has a fixture needing neither).
- Reporting and exports are paged and server-filtered: assume more than one page.
- Web: `domains/assess` composes capabilities; permission gates use `can()`, never a role.
  Four skins share tokens (`docs/DESIGN.md`): no literal colours.
- A feature touching these files runs every arm's journey that renders them
  (`docs/CORE-JOURNEYS.md`, `npm run e2e:assess` against a local api on :8002).
- Institution and hire are not consumers: no Payments/Referrals tabs, plan or trial copy, upgrade modal,
  "personal practice" link, Community, A to Z, Slides, Podcast or Athena (`athenaOffered` in
  `surfaces/jumpTo.ts`). Shared train screens take `surface !== "train"` and use the "ask your administrator" wording.
- **The board and console are pushed, not polled by heartbeat.** `snapshot_on_heartbeat=True` is allowed only in `voice/service.py` and `health/service.py` (`test_no_heartbeat_snapshots`). Every write that changes what the console shows must announce: clock and sitting writes call `announcements.circuit_changed`; an attempt moving status on a slot calls `sittings_reads.attempt_progress(session, attempt)` (attempts cannot import `announcements`; it is re-exported by `service_reads`); ending a person's unstarted stations announces `candidate_absent`. A new write that changes a console fact without one leaves the screen stale. Time-derived alerts (`no_running_attempt` after 20 s, `clock_overdue`) only appear on the next event now.
- **Reports are batched.** `sitting_detail` reads slots with one `slots_for_circuits`; report and cohort group slots by candidate once. The results CSV is a generator (`stream_sitting_results_csv`) and the audit row is written before the first byte. Roster import is `INSERT ... ON CONFLICT DO NOTHING` per row inside `begin_nested()`; any `AppError` skips that row with its code. `released_outcomes` tests released-ness on the current revision only (an older released revision never counts).

- **Circuits and breaks.** An exam-mode circuit is one candidate; a training circuit needs one station per trainee and has no breaks (`domain_run`). The exam's break is `exams.settings.default_break_minutes` (1 to 60, no column); the Schedule wizard seeds from it (`examTimings`). Sitting and org rows carry `circuit_count`/`candidate_count` from one aggregate (`totals_for_sittings`): never count per sitting. `overdue_seconds` is derived from `phase_ends_at`/`paused_at`; `voice_fault` shadows `clock_overdue`, so a test cannot assert both. "N not joined" is `OrgCounts.invited_not_joined`.
- **In a worktree, `poetry run` and `make` use a fresh venv with no deps**: put the main venv's `bin` on PATH, set `PYTHONPATH=.`, and run `ruff`, `mypy app`, `pytest -n auto` directly.

## What a failure looks like here
- A candidate is locked out of, or dropped from, a sitting partway through.
- The browser's clock decides a phase instead of the server's.
- One organisation sees or acts on another's sittings, roster or results.
- `users.id` and `trainees.id` mixed up, so the decision lands on the wrong person.
- A list or export reads one page and drops the rest.
