# Workspaces and arms

## Sub-features
- One route, `/app/<workspace>/<screen>`, rendered by whichever arm the workspace is.
- Consumer (`me`), institution (`kings`, `st-marys`), partner (`bmj`), platform staff (`/staff`).
- A screen that belongs to another arm, or a workspace you are not in, is "Page not found".

## How to get to it (user POV)
After sign-in, `/app/me` is your own practice. The workspace switcher and
direct URLs reach the others.

## Driving it with playwright-core
| Path | Ready when | Expect |
|---|---|---|
| `/app/me/dashboard` | h1 "Dashboard" | `navigation "Train sections"`: Dashboard, AI Practice, A to Z, Slides, Podcast, Articles, Contact & Feedback, Community, Marketplace, Settings, Achievements |
| `/app/kings/dashboard` | h1 "Kings College" | `navigation "Institution sections"`: Overview, Sittings, My training, Self practice, Practice sessions, Now running, Trainees, Team, Authoring, Stations, A to Z, … |
| `/app/bmj/dashboard` | h1 "Overview" | Arrivals / Signed up / Purchased, h2 "Tracking references" |
| `/staff` | h1 "Hello, Walkthrough." | links Organisations, Users, Authoring, Your account; h2 "Needs attention (0)" |
| `/app/nowhere/dashboard`, `/app/me/trainee`, `/app/me/stations`, `/app/kings/mocks` | h1 "Page not found" | link "Go to your workspace" |

Assert with `run.page.getByRole("navigation", { name: "Train sections" })`
and link names, then `proof()` each.

## Gotchas
- `/app/me/dashboard` shows `status "Loading"` for a while on first compile;
  wait for the h1, never screenshot on `networkidle`.
- The consumer dashboard fires ~13 parallel `GET /me/dashboard` on mount
  (`useCurrentExam` fetches per instance). Known; count it so a regression
  from 13 to a real loop is visible.
- The dev server logs a hydration-attribute mismatch warning on first load.
  Known; anything beyond it in `problems` is new.
- The staff page shows the user count (~1,298 real imported accounts). Do not
  open the Users directory in a proof; it prints real emails.
