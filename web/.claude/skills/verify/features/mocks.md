# AI Practice (mocks)

## Sub-features
- `/app/me/mocks` with tabs Setup, Consultation Tips (SCA only), Combine
  Stations, Flagged Stations; the tab lives in `?tab=` (`tips`, `combine`,
  `flagged`; none means setup).
- Setup: read-only name `Session N`, number of stations, **Create Session**
  (lands on `/mocks/{id}`), **View All Sessions** (`/mocks/list`). An account
  with no exam date gets the "Exam date" modal first; a `not_entitled` create
  opens the plan picker.
- `/mocks/list`: "<EXAM> Sessions", cards (the edit pencil and bin are hidden for learners since 2026-10-14)
  and bin (Confirm deletion modal, then a "Session deleted" toast).
- `/mocks/{id}`: rules, the microphone check, **Start Session** (or "Allow your
  microphone to start", aria-disabled), then the stations table once attempted.
- `/mocks/{id}/update`: redirects to the detail page for learners (edit screen commented out).
- `/mocks/{id}/complete`: "Well done", station outcomes, **New session** /
  **Review session**, and for SCA the "Keep practising" peer cards.

## How to get to it (user POV)
Nav **AI Practice** → Setup → **Create Session** → the rules page → **Start
Session**. After the last station, the complete page. **View All Sessions**
reaches the list (no rename or delete for learners).

## Driving it with playwright-core
```js
await page.evaluate(() => sessionStorage.setItem("exam_date_prompt_skipped", "1"));
await open(run, "/app/me/mocks");
await page.getByRole("button", { name: "Create Session" }).click();
await page.waitForURL(/\/app\/me\/mocks\/[0-9a-f-]{36}$/);
await open(run, `${setHref}/update`);
await page.getByLabel("Give your session a name").fill("Verify rename");
await page.getByRole("button", { name: "Update session" }).click();
await page.getByText("Session has been updated successfully.").waitFor();
await open(run, "/app/me/mocks/list");
await page.getByRole("button", { name: "Delete Verify rename" }).click();
await page.getByRole("dialog").getByRole("button", { name: "Delete" }).click();
await page.getByText("Session deleted").waitFor();
```
Handles: `getByRole("button", { name: "Edit <name>" | "Delete <name>" })`,
`getByRole("list", { name: "Station outcomes" })`, `getByRole("link", { name:
"Start Session" })`, `getByRole("button", { name: "I don't have a date yet" })`.

## Gotchas
- The exam-date skip key is `exam_date_prompt_skipped` = `"1"` in
  sessionStorage; any other value still shows the modal and blocks clicks.
- walkthrough@example.com's older sets ("probe", "Smoke session …") point at
  versions no longer in the library: titles fall back to "Station N" and
  **Start Session** fails with "A circuit can only use a published station".
  Create a fresh session to see titles and a working start; delete it after.
- The headless browser grants a fake microphone ("Fake Default Audio Input"),
  so the mic check reads ready and Start is enabled.
- Screenshot the delete modal after ~800ms; earlier catches the fade-in.
- A `/complete` or station page can time out on its first hit while webpack
  compiles; rerun once.
- The login page's `GET /api/v1/auth/sso/sign-in?host=localhost` 404 makes
  `finish()` exit 1 on every run; it is not a mocks problem.
- Free stations run out after three created sessions on an account ("You do
  not have access to this exam" plus the plan modal); reuse a session by URL
  (`.verify/fix-web1-consumer.mjs` takes `SET_URL`). Repeated sign-ins as
  walkthrough@example.com also hit "Too many attempts": wait a minute.
- The Attempts X/Y pill only moves when the voice worker bootstraps the
  attempt (consultation actually starts), not when the station page opens it;
  `SetStation` re-reads the session when the room goes live. Without a local
  worker the pill stays 0/N.
- Flagged stations shows its "Combine into a session" button only when a
  station is flagged. Flag one from the station header
  (`Flag this station to come back to`, a toggle).
- The Start session button is a link only when the mic is ready and the
  session has a station; otherwise a disabled button (block the mic with an
  `addInitScript` rejecting `getUserMedia` and a denied `permissions.query`).
- Unknown exam: force `**/api/v1/me/dashboard` to 502 with `page.route` after `signIn`. `/mocks` and `?tab=combine` then show only "We don't know your exam yet" (no progress bar, no form, no plans); the Consultation tips tab is also hidden (SCA only).
