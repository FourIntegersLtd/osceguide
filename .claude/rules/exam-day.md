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
