# Sign-in and session

## Sub-features
- Signed-out visit to a workspace page redirects to `/login?next=<path>`.
- Sign in with email and password; lands on `/app/me`.
- Reload keeps the session (httpOnly cookies via `/api/session`, refreshed by `/api/session/token`).
- Sign out from the nav lands on `/login`; workspace pages redirect to login again.

## How to get to it (user POV)
Open `/app/me/dashboard` in a fresh browser → sent to the login form → fill
Email and Password → **Sign in** → the personal workspace. Reload the page. Use
**Sign out** (bottom of the consumer nav; top banner on an institution).

## Driving it with playwright-core
```js
await open(run, "/app/me/dashboard", { ready: (p) => p.getByLabel("Email") });
// expect run.page.url() to end with /login?next=%2Fapp%2Fme%2Fdashboard
await signIn(run);                                     // -> /app/me
await open(run, "/app/me/dashboard");                  // h1 "Where you stand"
await run.page.reload({ waitUntil: "domcontentloaded" });
await run.page.getByRole("heading", { level: 1 }).waitFor();
// expect the URL is still /app/me/dashboard, not /login
await run.page.getByRole("button", { name: "Sign out" }).click();
```
Handles: `getByLabel("Email")`, `getByLabel("Password", { exact: true })`,
`getByRole("button", { name: "Sign in", exact: true })`,
`getByRole("button", { name: "Continue without analytics" })` (cookie dialog).

## Gotchas
- **Hydrate `/login` before submitting** (`networkidle` + 1.5s, which `signIn`
  does). Submitting the server HTML posts the form as a GET, every later page
  bounces to `/login?next=`, and it looks exactly like a session bug.
- A fresh browser gets the cookie dialog; its scrim swallows the Sign in click.
- The reload check is the one that matters: CI was green while the app signed
  everyone out on reload.
- `/login` asks `GET /api/v1/auth/sso/sign-in?host=localhost` and gets 200
  `null` (no SSO for this host). A 404 there means the api is older than
  2026-10-03, when it stopped answering 404 for "no SSO".
- A session check that fails with a gateway error (not a 401) is retried by
  the client, then shows "We could not check your session" with "Try again"
  rather than the "Checking your session" spinner.
- Signing in as a real imported user is never acceptable, even read-only.
