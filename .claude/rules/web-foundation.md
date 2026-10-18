---
paths:
  - "web/src/foundation/**"
  - "web/src/surfaces/**"
  - "web/src/app/**"
  - "web/src/domains/{train,marketing}/**"
  - "web/src/capabilities/*.ts"
  - "web/scripts/**"
  - "web/e2e/**"
  - "api/app/features/dashboard/{service,service_performance,service_achievements,router_achievements}.py"
---
# Web foundation: what to know

Owner: `web-foundation-owner`. Proof: platform-web `verify` skill (`web/.claude/skills/verify/`).
Other owners own the behaviour of their screens; this owner owns how everything is built.

## The one rule
Tiers import downwards only, lint-enforced: `app -> surfaces -> domains -> capabilities -> foundation`.
A capability may not import a domain or surface; take arm-specific things as a prop or from
`useSurface()`. A screen only consumers see: `domains/train`; only institutions: `domains/assess`;
both: `capabilities/<name>`; a button, card or token: `foundation/ui`; an API call: the owning
slice's `api.ts`; a route: `app/**`, composing and holding no logic. A new capability needs a
`capability.ts` declaring its `surfaces` and a `capabilities/registry.ts` entry.

## Non-negotiable
- One HTTP path: `platformRequest` from `foundation/platform-client`. No axios, no bare `fetch`.
- Branch on `PlatformError.code`, never `message`.
- Every load goes through `useAsync` + `AsyncBoundary`; a failure must never render as "no data".
- Colours come from tokens (`bg-canvas`, `text-ink`, `bg-accent`), never `bg-blue-600`; read
  `docs/DESIGN.md` for UI work (no black borders or black text).
- The exam clock is the server's. Strict types, no `any`.
- Do not hand-declare API types: regenerate (`make openapi`, `npm run platform:types`, `npm run types`).
  `schema.d.ts` is one generated file; one writer at a time.

## Traps a browser run has hit
- `/app/me/**` shows the exam picker, not the page, while `users.exam_code` is null: set it for a
  local test account.
- A node test cannot import a `.tsx` (the loader strips types, not JSX): put a pure helper in a `.ts`.
- `npm run ci` cannot see a backend field rename (types come from a possibly stale document);
  `node scripts/smoke.mjs` can, against a live platform-api. Run it whenever an `api.ts` changes.
- Green CI once shipped an app that signed everyone out on reload: prove in a real browser.
- The web dev server proxies `/api/v1` to a REMOTE api unless routed locally; never create data on a
  remote server. Journeys: `docs/CORE-JOURNEYS.md`, `npm run e2e` against :8002.
- CI runs the journeys on a FRESH database: a spec that passes only on your dev DB (templates, a
  library, a plan on sale) is red there. `e2e/global-setup.ts` makes every precondition or fails
  naming the seed; reproduce on a fresh database, not the dev one.
- Node is not on the default PATH: `export PATH="$HOME/.nvm/versions/node/v22.22.3/bin:$PATH"`.
- Learner read models (home, performance, achievements) are in api `dashboard/`; they exist only to
  feed these screens. A stored rubric structure is read via `rubrics.service`, never directly.
- This is not the Next.js you know: read `node_modules/next/dist/docs/` before writing code.
- A day is picked with `foundation/ui/DatePicker` (react-day-picker); keep days as `YYYY-MM-DD` via
  `dateDay.ts`, never `new Date("YYYY-MM-DD")` (UTC) for a calendar. Exam date has no time of day.
- Verifying from a git worktree: `npm ci`, copy `web/.env.local` in, run `npm run dev -- -p 3101` and
  pass `VERIFY_WEB_URL`; `npx playwright test` starts its own :3101, so stop yours first, and
  its global setup registers accounts (api rate-limits: wait a minute between runs).
- The shell (`surfaces/Workspace*`): Help is an outline-variant button with Athena's face in the toolbar (md up) and the
  floating `AthenaFab` on phones (`md:hidden`); both fire `osce:open-athena`, and the dock shows the FAB on Train and the staff console only (`athenaOffered`, `capabilities/surface.ts`), and there
  on every route, never behind a route gate. The toolbar carries the Notifications bell (the inbox, path `/notifications`, `/inbox`
  redirects) with the unread count; the sidebar item has no badge. The exam countdown is one line under
  the workspace name (`examDetail`), never in the footer. Voice Athena is off Contact, Notifications,
  Settings and Community (`helpPersona.ts`): the dock there is text `Help` only. Search (⌘K, `WorkspaceJumpTo` + `jumpToSearch.ts`) is pages, then stations and Help
  articles (existing GETs, 250ms debounce, 2+ chars, stations on Train only) and an "Ask Athena" row ("Help with ..." where voice is off, `helpPersona`); it
  never calls knowledge-chat per keystroke. Icons are `react-icons/lu` only, one literal icon per item.
- A gate in a lazy placeholder and in the component it loads must agree: the Help button showed, then
  vanished when the dock loaded. A route gate on a shared control needs a journey at the width where
  nothing else offers it (`e2e/train/help-everywhere.spec.ts` runs at phone width).
- Page width is the shell's one container: a page under `app/app` and the screens it mounts set no `max-w-*`
  (`surfaces/pageWidth.test.ts` guards it). Toasts are top-centre and one with `durationMs` is capped at 60 s
  (`toastDuration.ts`); success feedback is a `useToast` toast, not an inline Alert. `Panel` is static; a part that folds is `FoldSection`. The Help button and FAB use a neutral `LuCircleHelp`, never Athena's face. `resolveCrumb` takes an options object; section and deep-page names are the one `NAV_LABELS` map. A confirm step is `foundation/ui/ConfirmModal`. Study search types into the URL
  (`useStudySearch`); A to Z and Podcasts load the whole catalogue once and page client-side (`catalogue.ts`).
- The page column (`b2cPageColumn`) is the scroller (its `overflow-x-hidden` makes it one) and a sticky child is offset by the scroller's own padding: keep top padding on an inner div (`WorkspaceShell`), never on `main` or the column, so `sticky top-0` sits flush under the 52px toolbar. Contact subject and the testimonial question are pure models (`contactSubject.ts`, `productFeedbackModel.ts`).
- A live room (`b2cRoomOverlay`: station, peer) is its own scroller. Its fill chain (`b2cRoomFill`, min-h-0 flex-1)
  is `lg:` only: below lg the panes stack at natural height. A fixed-height flex column on a phone clipped the
  doctor information and nothing scrolled. `e2e/train/phone-layout.spec.ts` (TRAIN-8) guards every route at 390px.
- `dismissOverlays` checks once (`isVisible` does not wait): a modal mounting after it (the exam-date prompt after a
  capability gate bounces `/stations` to `/mocks`) holds the page. Skip it by its sessionStorage key. A journey that
  starts a station uses its own world account (`runner`): a session with an attempt cannot be deleted,
  and TRAIN-3 expects the consumer's one session.
- Public page head: set it with `publicPageMetadata` (`app/metadata.ts`); the root sets no canonical (it was inherited by every page and made the site canonicalise to `/`). `title.template` does not apply to `app/page.tsx` (same segment as the layout): write that title in full. `e2e/public/seo.spec.ts` fetches each `PUBLIC_MARKETING_PATHS` page with no JS (canonical, description, unique title, one h1, word floor); a new public page goes in that list. `/` is server HTML; the signed-in redirect to `/app` is in `middleware.ts` on the `osce_rt` cookie.
- Open items: `docs/BACKLOG.md`; delete a row when you land it.

## What a failure looks like here
- A load failure rendered as "no data", or a branch on `message` instead of `code`.
- A tier imported upwards, a bare `fetch`, or a hand-declared API type.
- A literal colour, an authoritative browser clock, or a gate where the lazy placeholder and loaded component disagree.
- Works on the dev database or at desktop width only.
Skip `schema.d.ts`, `openapi.json` and `_generated/`: they are generated.
