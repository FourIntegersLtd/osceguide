# Exams and staff study media

## Sub-features
- Exams: `/staff/authoring/exams` (platform catalogue) and
  `/app/{org}/authoring/exams` (an organisation's own). Row icons are buttons
  named by their tooltip: **Edit**, **Publish** (drafts only; named "Choose a
  rubric version first" and disabled until the exam names a rubric),
  **Retire** (published only, behind a "Retire …?" confirm), **Delete** (org
  scope only, behind a "Delete …?" confirm; the platform catalogue has none).
  The Create/Edit dialog's fields are named Code, Name, Reading time
  (seconds), Station time (seconds), Attempts per station, Rubric version.
- Staff media: `/staff/media?new=1&kind=<kind>` opens the "New …" dialog;
  `/staff/media/{id}` is the detail. A draft has **Delete draft** (confirm
  dialog); a published item has read-only content, keeps **Save** for title,
  summary and exam, and loses **Save and publish** and **Edit as JSON**.
  Spoken kinds (summary, deck, podcast) show the step rail; its **Check
  facts** step lists claims with **Make this change** / **Remove it** /
  **Keep as written**, hidden while a job runs (`content.status` producing,
  checking_facts, writing_script, generating*).

## How to get to it (user POV)
Staff menu → Authoring → Exams; Staff menu → Study media → a kind's tab →
New, or a row.

## Driving it with playwright-core
`.verify/fix-content2.mjs` drives all of the above with its own fixtures
(`walkthrough@example.com`; its org is `st-marys`, not `kings`). Find a row
with `getByText(name, { exact: true })` then its nearest ancestor `div` that
holds an **Edit** button.

## Gotchas
- The org exam list hides drafts until **Drafts only** is ticked.
- An org station can only be filed under a published exam, and publishing
  needs a rubric version: take one from `GET /orgs/{org}/rubrics`.
- A media item's content cannot be PATCHed while it is running, and
  `stop-produce` does not settle without the worker; to show the "running"
  state, PATCH `content.status` to `producing` from an idle item.
- A blank new item is named "Untitled <kind> <date, time>": the slug comes
  from the title, so a plain "Untitled summary" clashed (`slug_taken`) on the
  second one.
- Deleting a draft that was published meanwhile is the easy way to provoke a
  refusal inside a confirm dialog (`media_not_deletable`).
