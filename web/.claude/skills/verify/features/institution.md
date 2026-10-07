# Institution dashboard and sittings

## Sub-features
- Dashboard: setup rail ("Getting started": next-step bar plus eight steps, Marking scheme to First sitting; hidden when all done); roster Status column (Added/Invited/Accepted/Member/Booked, amber when stuck), "At a glance" counts, recent sittings.
- Sittings list and "Schedule a sitting".
- Build (nav entry for staff, `/authoring`): tabs Marking schemes, Exams, Programmes, Templates, Stations; opens on Marking schemes.
- People (nav, `/trainees`): tabs Trainees and Team (Team only with `manage_team`).
- Programmes (no nav entry; `/programmes` still works): the real list, same as Build → Programmes. Button "New programme",
  dialog "Add programme" (input "Exam code"). Row action: "Activate" (draft), "Retire" (active), "Reactivate" (retired).
  Above it, section "Exams the platform publishes": rows with button "Adopt" (org admin) or badge "Adopted";
  the setup guide's Exam step ("Adopt or write an exam") links here.
- Results → "Open <name>" → "The decision": Pass/Fail buttons, rationale, "Sign off"; once signed off,
  "Back to draft" (confirm dialog, same label) and "Release". Exam-mode sittings add select "Recruitment outcome";
  released shows "Recruitment outcome: <label>" (options include "Pending", "Reserve list"; "Not recorded" is the blank).
- Slot review (`/slots/<slotId>/review?sitting=<id>`): the admin's review panel, buttons "Save draft" and
  "Complete review"; completing with domains unrated shows "...still missing: <domain titles>".
- Candidate (needs a `trainee` membership, see B57): `/trainee/sittings/<id>` shows the reading brief during
  reading and "Read your result" once released; `/trainee/results/<id>`, `/trainee/reviews/<slotId>`.
- Circuit runner (`/circuits/<id>`): "Start circuit"; "End circuit" then dialog "End the circuit".
- A supervisor sees no "Schedule a sitting" on the dashboard or the sittings list (`schedule_sittings`).

## How to get to it (user POV)
Switch to St Mary's (`st-marys`; `kings` may not exist locally) → Overview. Staff nav: Overview, Sittings, Now running,
People, Build, Settings. A trainee sees My training, Practice sessions, Self practice, Stations, study, Community, Settings.

## Driving it with playwright-core
```js
await open(run, "/app/kings/dashboard");      // h1 "Kings College"
// links: "Continue setting up", "Trainees 4", "Staff 2", "Your stations 0", "Sittings 0", "All sittings"
await open(run, "/app/kings/sittings");       // h1 "Sittings", link "Schedule a sitting", "No sittings yet"
await open(run, "/app/kings/authoring", {     // redirects to /authoring/rubrics
  ready: (p) => p.getByRole("tablist", { name: "Authoring section" }),
});
// tab "Marking schemes" [selected]; click tab "Stations" for button "New station", combobox "Filter by exam"
```

## Gotchas
- `/app/kings/authoring` redirects to `/app/kings/authoring/rubrics`; before
  it settles `<main>` is empty, which looks like a broken page. Wait for the tablist.
- Counts are seed data and drift; assert the labels, and quote numbers only as
  "was N at the time".
- Scheduling a sitting writes data. Do it only in `kings`/`st-marys` and
  record it in the run log.
