# Rubric builder

## Sub-features
- Start chooser: blank, a platform rubric, or (in an org) one of its own; server-side search; the title is set here only.
- Builder tabs Domains / Scale / Pass rule / Feedback / Advanced / Trial mark / Versions (`?tab=`), each with a problem count; Back/Next footer.
- Domains tab: dnd outline of domains and competencies, Add menu, row menu, detail panel (inline at xl, modal below).
- Problems: every backend `{path, message}` pinned under its input (`[data-path]`), plus the list in the aside;
  Publish disabled with the reason in the status bar.
- Preview (Feedback page / Dashboard) from the backend's sample result; Trial mark (pasted transcript or attempt id) over SSE.
- Read-only for a published version or a platform rubric seen from an org ("New draft version", "Copy to my rubrics").

## How to get to it (user POV)
Staff: Authoring → Marking schemes → Create marking scheme (org: Build → Marking schemes) (`/staff/authoring/rubrics/new`). Org: `/app/<org>/authoring/rubrics/new`.
The builder is `…/authoring/rubrics/<rubricId>/versions/<version>`.

## Driving it with playwright-core
```js
await open(run, "/staff/authoring/rubrics/new", { ready: (p) => p.getByRole("radiogroup", { name: "Start from" }) });
await page.getByLabel("Title").fill("Verify SCA copy");
await page.getByRole("radio").filter({ hasText: "Simulated Consultation" }).first().click();
await page.getByRole("button", { name: "Copy and edit" }).click();          // "Start blank" for the blank card
await page.getByRole("tablist", { name: "Marking scheme" }).waitFor();
await page.getByRole("tab", { name: /Trial mark$/ }).click();               // tab names may carry a problem count: anchor with $
await page.getByLabel("Transcript").fill("Doctor: …\nPatient: …");
await page.getByRole("button", { name: "Trial mark" }).click();
await page.locator("text=/^(Marked|Failed) ·/").first().waitFor({ timeout: 240_000 }); // ~45 s, real model
await page.getByRole("button", { name: "Publish", exact: true }).click();    // then "This version is read-only"
```
Scripts: `.verify/rubric-builder.mjs` (staff, SCA copy end to end), `.verify/rubric-blank.mjs` (org, blank).
The org run needs an org: `review-slot-fixture.sql` (`verify-r3`), removed by `review-slot-teardown.sql`
(which also deletes that org's rubrics). Run both with
`docker exec -i platform-api-postgres-1 psql -U postgres -d osce_platform < file`.

## Gotchas
- **Rows are collapsed**: a competency is edited in the detail panel after clicking its row. Viewport shots are enough.
- **Publish is a ConfirmModal** and the "Published" notice lives in `?published=1`, so it survives the reload.
- **Publish stays disabled after a valid edit until it is saved** ("Save your changes to publish."): the backend
  publishes the saved version. Restoring a field to its saved value makes the draft clean again.
- **A trial marks the saved version**, so the builder saves a dirty draft first; it is rate-limited (20 an hour).
- **A copied rubric is valid at once**, so Publish is enabled straight after "Copy and edit".
- Staff-created platform rubrics show on every org's start chooser: delete them after a run
  (`delete from rubric_versions … ; delete from rubrics where owner_kind='platform' and title='…'`).
- The 404 on `/api/v1/auth/sso/sign-in?host=localhost` is the login page's SSO probe, not a builder failure.
