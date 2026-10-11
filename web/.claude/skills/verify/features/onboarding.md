# Athena onboarding (voice)

## Sub-features
- Opens one assistant session (`POST /api/v1/assistant/sessions`, profile `onboarding`) and one voice token.
- Step 1 is the choice: "Turn on Athena's voice" or "Continue without voice", with "Pick voice or text first" under them. "Show me how it works" is not rendered until voice is on or text is chosen (C-50).
- Three steps (Meet Athena, Watch a demo consultation, Your first station), then "Start my first consultation" (dashboard: → `/mocks`). "Skip tour" shows on steps 1 and 2 only. Neither host renders the modal's close X; Escape and the backdrop still close it and remember it (`osce_onboarding_dismissed:{exam}:{user}`) (C-52).
- Text demo: headings "Patient", "Athena" (the question), "You" (the reply) and "Athena · What you could have said" (the model answer). Locate them with `getByRole("heading", { name, exact: true })`: "You" also matches the model-answer heading otherwise.

## How to get to it (user POV)
A modal over the consumer dashboard (`ExamDashboard`), opened automatically for a new account with no attempts, or replayed from account preferences. There is no `/app/me/onboarding` route (removed in e1d6f96, which is deliberate).

## Driving it with playwright-core
```js
const calls = [];
run.page.on("request", (r) => { if (r.url().includes("/assistant/sessions")) calls.push(r.method() + " " + r.url()); });
await open(run, "/app/me", {
  ready: (p) => p.getByRole("button", { name: "Show me how it works" }), settle: 10_000,
});
// expect calls.filter(c => c.endsWith("/assistant/sessions")).length <= 2
await proof(run, "onboarding");
```
Handles: "Athena" title, button "Show me how it works", the dialog's Close
button, status text "Connecting to Athena…" / "Not connected".

## Gotchas
- **Count the session POSTs.** A re-render loop once opened 3,144 sessions in
  15s (a fresh `useMicPreflight` object each render → new `start` → effect
  re-fired). Each is billed voice in production. Expected now: 2 per visit
  (one extra from a remount, not yet traced); anything more is a regression.
- Headless Chrome blocks the microphone unless the harness's fake-media flags
  and `permissions: ["microphone"]` are set; without them the screen stops at
  "Your browser is blocking the microphone".
- One microphone request per visit, made by the session start and capped at
  10s. A second concurrent `getUserMedia` (the old microphone card) hung the
  walkthrough on an installed iOS app; do not add one back.
- Locally no assistant worker joins, so "Show me how it works" stays disabled
  and the status stays "Connecting…". That is the environment, not a bug.
- `make start` runs uvicorn `--reload`: an edit in backend/ mid-run drops
  in-flight requests, and the proxy reports `500 … socket hang up`. Check
  `api.log` for "Reloading" before calling a 500 real.
