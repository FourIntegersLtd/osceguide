# Marketplace and live peer practice

## Sub-features
- `/app/me/marketplace` (SCA only; `/peers` is gone): tabs **All Sessions**,
  **My Sessions**, **Upcoming Sessions**; **Post Availability** (date grid,
  "Choose a time" listbox, **Select & continue**); **Claim slot** with a
  confirm modal; cancelling an upcoming booking.
- **Live Practice** prompt → **Join now** → "Searching for a practice partner"
  modal, then the bottom-right "Finding a practice partner" card with
  **Leave Queue**.
- Match: "Practice partner found" with a "Time to respond" countdown read from
  `accept_expires_at` (two minutes). **Start Session** calls `/accept`; **Not
  Now** and the countdown reaching zero call `/decline`.
- `/app/me/marketplace/session/{id}`: "Waiting for your partner to join..."
  (with "Partner didn't show? Report no-show"), then Preparation Phase, Live
  Consultation (video tiles, Time Warning at 6 min, Time's up), Debrief;
  **End Session** confirm (copy differs by phase and time left); **Report
  abuse** modal.
- Exits: partner ends → "Partner Left" (requeue or dashboard); partner declines
  after you accepted → "Session no longer available" and you are already back
  in the queue (`requeued_entry_id`); session ends → `/feedback`
  ("Session Completed", Yes/No, stars, comment, **Submit Feedback** / **Skip**).

## How to get to it (user POV)
Nav **Marketplace** (SCA accounts only) → Live Practice → Join now. The second
person does the same in another browser; both see the match modal.

## Driving it with playwright-core
Two accounts, two browsers: `walkthrough@example.com` and
`peer-partner@example.com` (password `correct horse battery`). The full run is
`.verify/marketplace-exact.mjs` (about 7 minutes; wrap it in
`perl -e 'alarm 560; exec @ARGV' node ...`, zsh has no `timeout`).
```js
const dialog = (page) => page.locator('[role="dialog"]:visible').last();
await page.getByRole("button", { name: "Live Practice" }).first().click();
await dialog(page).getByRole("button", { name: "Join now" }).click();
await page.getByText("Practice partner found").first().waitFor({ timeout: 45000 });
await page.getByRole("button", { name: "Start Session" }).click();
// Fast-forward a phase, then reload: the page only re-reads the clock on load
// or when its own phase_ends_at timer fires.
sql(`update practice_sessions set phase_ends_at = now() + interval '3 seconds' where id='${sid}'`);
await page.reload();
```
Handles: `getByRole("tab", { name: /Upcoming Sessions/ })`,
`getByRole("button", { name: "4 stars" })`, `getByRole("button", { name:
"Yes, End Session" })`, `getByRole("button", { name: "Close", exact: true })`.

## Gotchas
- Matching runs in the **worker** (`make worker` in platform-api). Without it
  nobody is ever matched. Restart it after a backend change.
- Clear leftovers first: waiting queue entries and open sessions for both
  accounts (the script's first two SQL lines), or `join` lands on an old
  session.
- walkthrough is a platform admin and lands on `/staff` after sign-in; open
  `/app/me/marketplace` directly.
- Time Warning and Got it modals re-open after a reload inside the last six
  minutes and intercept clicks. Click every visible **Got it** after each
  reload.
- Give a phase at least 25 s after a DB fast-forward. A reload that compiles
  slowly can land after the transition, and then no Time's up modal appears.
- Shorten `accept_expires_at` in the DB, then reload the page whose countdown
  you are testing: the modal reads the deadline once.
- Dialogs render in a portal, so the harness's `main` aria snapshot does not
  contain them. Read the PNG.
- No recording bucket locally: consultation recording is skipped, which is
  expected.
- `/me/dashboard` is fetched about a dozen times per page (W-3); it is noise,
  not a marketplace fault.
- A 5xx on `/me` (seen as a Next proxy `ECONNRESET`) signs the browser out and
  bounces to `/login` (S-1 in BACKLOG). If a run lands on the login form
  mid-flow, check `web.log` for `Failed to proxy .../api/v1/me` before
  blaming marketplace code.
- The login page's `GET /api/v1/auth/sso/sign-in?host=localhost` 404 is
  always in the problems list.
