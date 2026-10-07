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
- **Check where `/api/v1` really goes.** The dev server proxies it to
  `PLATFORM_API_URL`, which `.env.local` can point at a remote api (2026-10-07
  it answered from Cloudflare). Then the browser signs in against another
  database while your SQL reads the local one: a disabled-password flag "does
  nothing", a reset token is "no longer valid", a web sign-up has no row.
  Probe with `curl -s localhost:3100/api/v1/health -D - | grep server`
  (uvicorn is local). If it is remote, route the browser to this checkout:
  `context.route("**/api/v1/**", r => r.request().url().includes("/stream") ? r.abort() : r.fulfill({ response: await r.fetch({ url: r.request().url().replace(WEB, API) }) }))`.
  Abort the event streams: a fetched stream never ends and hangs the route.
- SSO callback: `/auth/sso/callback?org_slug=x&error=sso_verification_failed`
  shows the refused-SSO copy; any `token=` is stripped from the address once
  read, so a reload says "already been used". Signed in, it posts nothing and
  says "You're already signed in, so this organisation sign-in link was not
  used", with a "Continue to your account" button.
- Undelivered email on `/staff/ops`: mark a row `status='failed', attempts=12`
  in `outbound_messages`; each row is a `listitem` with a "Retry" button, and
  the retry is audited in `audit_log` as `notifications.message_retried`.

## Forgot password and invitations
Handles: `/forgot-password` → `getByLabel("Email")`, button **Send reset link**, then
heading "Check your email". `/reset-password?token=` → `getByLabel("New password",
{ exact: true })`, `getByLabel("Confirm password")`, button **Save new password**.
`/accept-invitation?token=` is the same screen: label **Password**, button **Accept
invitation**, then "Your account is ready" with a **Sign in** button. An org admin
invites from `/app/<org>/team` → tab **Add people** → `getByLabel("Email address")`,
`getByLabel("Their role")`, button **Add person**.

The link is not sent locally: read the token from the outbox row,
`select payload->>'token' from outbound_messages where recipient=… and
template_key in ('password_reset','invitation')`. Expire a link with `update
password_reset_tokens set expires_at = now() - interval '1 minute'`. Driven end to end
by `.verify/fix-W2-reset.mjs` and `.verify/fix-W2-invite.mjs`.

- `password-reset` and `password-reset/confirm` share one rate limit: 5 per 5 minutes
  per caller. One full journey uses most of it; a second run inside the window gets
  429s that look like a broken link. Wait five minutes between runs.
- A spent or expired link answers 422 `invalid_reset_token`; the screen then offers
  **Send a new link** (reset) or **Sign in** (invitation). A deliberate refusal still
  logs a "Failed to load resource" console line; filter only that status.
- A script that routes `/api/v1` through `fix-common.mjs`'s `viaApi8013` must end
  with `process.exit(...)`: a signed-in org page opens EventSource streams, the proxy's
  `fetch` never finishes them, the script never exits, and the open connections stop
  uvicorn `--reload` from restarting (the api answers nothing until they close).
