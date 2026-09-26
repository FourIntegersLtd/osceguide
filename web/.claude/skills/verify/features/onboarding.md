# Athena onboarding (voice)

## Sub-features
- Opens one assistant session (`POST /api/v1/assistant/sessions`, profile `onboarding`) and one voice token.
- Joins a LiveKit room; "Show me how it works" enables once Athena is connected.
- Scenes, then a demo, then finish (→ `/mocks`) or "Skip the introduction" (→ `/dashboard`).

## How to get to it (user POV)
`/app/me/onboarding`, or "Start the guided tour" on the consumer dashboard.

## Driving it with playwright-core
```js
const calls = [];
run.page.on("request", (r) => { if (r.url().includes("/assistant/sessions")) calls.push(r.method() + " " + r.url()); });
await open(run, "/app/me/onboarding", {
  ready: (p) => p.getByRole("button", { name: "Skip the introduction" }), settle: 10_000,
});
// expect calls.filter(c => c.endsWith("/assistant/sessions")).length <= 2
await proof(run, "onboarding");
```
Handles: h3 "Athena", button "Show me how it works", button "Skip the
introduction", status text "Connecting to the patient…" / "Not connected".

## Gotchas
- **Count the session POSTs.** A re-render loop once opened 3,144 sessions in
  15s (a fresh `useMicPreflight` object each render → new `start` → effect
  re-fired). Each is billed voice in production. Expected now: 2 per visit
  (one extra from a remount, not yet traced); anything more is a regression.
- Headless Chrome blocks the microphone unless the harness's fake-media flags
  and `permissions: ["microphone"]` are set; without them the screen stops at
  "Your browser is blocking the microphone".
- Locally no assistant worker joins, so "Show me how it works" stays disabled
  and the status stays "Connecting…". That is the environment, not a bug.
- `make start` runs uvicorn `--reload`: an edit in backend/ mid-run drops
  in-flight requests, and the proxy reports `500 … socket hang up`. Check
  `api.log` for "Reloading" before calling a 500 real.
