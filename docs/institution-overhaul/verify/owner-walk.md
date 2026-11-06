# Owner walk: a new institution owner, local stack

Org `owner-walk`, owner olivia.owner@example.com. Real Chrome via Playwright, screenshots 01-93 in `docs/institution-overhaul/verify/owner-walk/` (some numbers repeat or skip). Registration is a request form; staff provision the org through the platform API and the invitation token is read from `outbound_messages.payload`.

## Step log
1. Register and first sign-in: request form, staff provisioned, invitation accepted, home shows the setup assistant.
2. Settings and People: invited an admin, a supervisor and an examiner (Admin and Supervisor roles only); no branding or logo exists; billing reachable.
3. Roster: single add (Amara), CSV import (3 added, 1 bad row dropped), year group "June 2026", group "Resit group".
4. Stations and templates: layout "Telephone consultation layout", station "Sore throat telephone consultation" published.
5. Marking scheme: blank scheme created, published, v1 Live.
6. Exam "Consultation skills mock": wizard, scheme attached, published, "Ready to schedule".
7. Sitting "November mock", formal, one circuit; circuit started (reading time shown on the live board), then ended.
8. Results: reviewed the results hub, home outcomes row and reporting. Slot review and release not walked: needs a marked-attempt fixture (`web/.claude/skills/verify/features/feedback-fixture.sql`).
9. Other: unknown route 404 page, invalid sitting page, empty states. Not walked: sitting edit/cancel, circuit delete, exam retire, trainee delete, staff revoke and last-admin guard, supervisor-invitation permissions pass.

## Confusion points
Fixed (web only):
- High. Schedule picker labelled invited, never-signed-in trainees "Signed in". Now "Invited, not accepted" / "Not joined yet" with Resend (`candidateStanding`).
- Medium. Schedule help and home attention row said unaccepted people cannot be scheduled; they can. Copy corrected.
- Medium. Circuit console said "Everyone is in." before anyone joined.
- Low. Reporting said "1 sittings · 1 candidates" (`reportingLine`).

Left (after the third pass, see "Third pass"):
- High (content-owner). Station creation for a custom exam with no layout is a dead end ("Save draft" disabled; "needs a template" contradicts "a station with no template is still a real station"). Layout editor shows engine words ("org-defined system prompt", "AI role"). "Layout" vs "template" used for one thing.
- Medium. Accept-invitation page cannot name the organisation (no read endpoint on the token page; api, additive). Register confirmation offers "Go to sign in" before an account exists.
- Medium. Settings has no branding/logo (product decision).
- Medium. Exam, Programme, Year group and Group still overlap as four words (product decision on the single word; "Set up an exam" now opens the New exam sheet).
- Low. No CSV template download.
- Builder (marking-owner, not edited): Pass rule says bands are set "under Advanced, in the JSON"; exam schemes carry the "formative training only" disclaimer in preview.

## Changed files (web)
`domains/assess/scheduleSitting.ts` (+test), `ScheduleSteps.tsx`, `sessions/SupervisorControls.tsx`, `reporting/api.ts`, `Reporting.tsx`, `reporting.test.ts`, `dashboard/support.ts` (+test).

## Second pass (final state)
Fixed in this pass (web only, no api change, no openapi change):
- High. Circuit console says "No one sat this circuit, so there is nothing to mark." when no station was sat (`circuitReviewSteps.ts`, test added). Home outcomes row no longer says "Every review is complete".
- Medium. Exam wizard says "domains" not "areas"; OSCE Guide's schemes are tagged "(OSCE Guide)" in the scheme picker. A taken exam code now names the exam or draft that holds it and where to continue it (`codeTakenMessage`, test added). "marking rubric" in option labels is the scheme's own title, data, not UI copy.
- Medium. Accept-invitation is a plain card (no consumer testimonial) and says "Your organisation has invited you". It still cannot name the organisation: the token page has no read endpoint for it (api, additive, left).
- Medium. Settings tabs read "Sign-in method" and "Automatic user sync", with a plain-words lead.
Walked in the second pass: sitting Edit (mode, exam and type lock once a circuit started: sensible), staff revoke with Restore, supervisor permissions (People read-only, Settings shows account only, exams list has no Edit/Retire/Delete, results visible), exam Retire and Delete controls present.
New finding, left (low-medium, api): revoking yourself succeeds when the only other admin has not accepted (`active_admins_besides` counts invited admins), and revoke has no confirm step.
Not walked: circuit delete and sitting cancel (no such control exists on the sitting or circuit page), trainee delete, slot review and release (no marked attempt in the local DB to bind a slot to; the fixture in `web/.claude/skills/verify/features/feedback-fixture.sql` needs existing marked attempts).
Still left: results-hub "Urgent review" and "needs a decision" for an absent candidate (index row has no "sat" count: additive api field plus openapi regen, not done), station creation dead end (content-owner), Exam/Programme/Year group/Group overlap, and the Low list above.

## Third pass (fixed, uncommitted)
- Results hub / home / console: the results index row now carries `sat` (additive; openapi and `schema.d.ts` not regenerated here). `undecided(row)` in `results/support.ts` caps "needs a decision" by who sat, so an absent candidate no longer shows "Urgent review"/"needs a decision"; the console already says "No one sat this circuit".
- Self-revoke: `active_admins_besides` counts only active, accepted admins (a sole accepted admin can no longer revoke themselves while the other is invited); the revoke dialog has a stronger line when it is you. Test actors are "invited" unless `make_actor(signed_in=True)`.
- Fixed: ExamDetail "Open scheme" with none chosen now "Find a scheme"; a platform exam we have not adopted reads "Not adopted yet", not "Not available"; bulk import stamps rows in file order (list no longer shuffles); CSV result counts file-dropped rows ("3 added, 1 skipped"); duplicate "Import trainees" heading; no spreadsheet block under "Add one person" (its tab remains); "Year groups" / "Year group name"; "Not scheduled" status for a dateless sitting; a 404 no longer offers "Try again"; reporting exam row opens that exam's sittings; home tile "Staff" (was "Supervisors" counting all staff); "Set up an exam" in the schedule wizard opens the New exam sheet.
- Skipped (product decision): single word for Exam/Programme/Year group/Group; accept-invitation organisation name (needs an api read); CSV template; branding; station-creation dead end (content-owner).
