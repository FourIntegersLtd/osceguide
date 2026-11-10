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
- There is ONE accent: `--brand` / `--brand-hover` / `--brand-pale` (+ hex twins) at the top of `web/src/foundation/ui/tokens.css`. Every surface (train, assess, hire, partner, staff) and the public site's `--site-brand` read it; no surface overrides it. Change the blue there only, and never write a literal blue in a component or chart (`rgb(var(--brand))`).

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
  A journey never picks a day of the current month: the 28th is past from the 29th on. Click
  next month first.
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
- Page width is the shell's one container, full width between equal gutters (no `max-w-*`/`mx-auto` on `b2cPageColumn`, `assessPage` or a screen's root; cap only paragraphs and forms, `e2e/support/phone.ts` `expectEvenGutters` measures it): a page under `app/app` and the screens it mounts set no `max-w-*`
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
- Never guess an exam from sets, stations or the catalogue: `useCurrentExam().code` null is "unknown". Filter exam-specific nav and routes through `examForFilter` (`surfaces/examNav.ts`; `capabilitiesFor` takes no null), and gate a screen that asks the api about an exam with `RequireExam` / `classifyExam` (`foundation/session`), whose only `ready` state carries a code (a `""` exam reads as an unpaid account and shows a subscriber the paywall). `e2e/train/null-exam.spec.ts` (TRAIN-13) is the only guard of that wiring: a node test cannot import a `.tsx`. Every `useCurrentExam` shares one store (`foundation/session/examStore.ts`): one request, one answer, one error; `reload` refreshes all instances with a real request, and the state is dropped at sign-out, a user change or when the last instance unmounts.
- No polling: a screen waits on SSE (`useMeEvents`); a timer may change display copy, never call the api. `web/scripts/check-no-polling.mjs` (in `npm run ci`) fails on `setInterval(` or a `setTimeout(` that calls the api or itself; its allow-list carries a reason per file and only shrinks. `PaymentReturn.tsx` is a known entry still to move to SSE.
- Open items: `docs/BACKLOG.md`; delete a row when you land it.

## Boards win on the institution surfaces
- Assess, hire and partner are drawn from `docs/institution-overhaul/boards/*.dc.html`; where DESIGN.md disagrees, change DESIGN.md. Use the `assess*` tokens in `b2bTokens.ts` and the `text-assess-*` sizes, never `text-[Npx]`.
- A new `text-assess-*` size must also be listed in the font-size group of `foundation/ui/cn.ts`, or `cn()` drops it next to a text colour. Tailwind colour keys are camelCase (`bg-osce-navActive`); a kebab name silently renders nothing.
- Prove with `e2e/support/board-diff.ts` (see the verify skill). The boards' `support.js` is not in the repo; `board-runtime.js` stands in. The harness pins the board sidebar to an integer width, because a fractional page x changes every glyph's anti-aliasing. The learner shell's `-webkit-font-smoothing: antialiased` is switched off on assess/hire/partner so text matches the boards.

- Named exceptions to the boards (user feedback 2026-11-05, in DESIGN.md "Spacing rhythm and quiet selection"): ample vertical spacing from the `assessForm*` tokens, and selection/focus as a 1px light-blue border plus a soft ring (`--assess-select-border`, `--assess-focus-ring`), never a saturated accent border. `Panel` gap classes go in `bodyClassName`; on `className` they silently do nothing.

## What a failure looks like here
- A load failure rendered as "no data", or a branch on `message` instead of `code`.
- A tier imported upwards, a bare `fetch`, or a hand-declared API type.
- A literal colour, an authoritative browser clock, or a gate where the lazy placeholder and loaded component disagree.
- Works on the dev database or at desktop width only.
Skip `schema.d.ts`, `openapi.json` and `_generated/`: they are generated.

## Public site chrome (landing, legal)

- Site tokens live in `web/src/foundation/ui/siteTokens.css` under `.site-root` (`--site-*`, light default, dark via `prefers-color-scheme` guarded by `:not([data-theme="light"])` plus `[data-theme="dark"]`); Tailwind names are `site.*`. Wrap public pages in `domains/marketing/site/SiteShell`; `SiteButton`, `SiteButtonLink`, `LogoLink` (the real `foundation/ui/Logo`, never an invented mark), `Eyebrow`, `SectionHead` and `IconTile` come from `@/foundation/ui` (files in `foundation/ui/site`). Footer and nav links live once in `domains/marketing/site/siteLinks.ts`.
- Product controls (Input, Select, Checkbox, FoldSection) have no dark skin; the auth pages scope dark overrides under `.site-root.site-auth` in `siteTokens.css`.
- Legal pages go through `domains/marketing/legal/LegalPage`. Legal text stays word for word: never renumber or fix headings in a restyle, report oddities instead. The "On this page" list is built client-side from `#legal-body h2`.
- Browser proof: the cookie modal covers the first viewport (click "Continue without analytics" before screenshots) and motion needs `reducedMotion: "reduce"`. No login needed.
- macOS `sed -i` needs `''`; edit with Python.

## Marketing pages (exam landings, /institutions)
- Every public page sits in `SiteShell` (`exam` keeps partner attribution on Login/Start free; `links` swaps the centre links, e.g. institutions anchors). No per-page nav or footer.
- Build bands from `home/Section`, `SectionHead`, `Eyebrow`, `IconTile`, `exam/ExamBlocks`; parameterise home sections (`HomePractice`, `HomeTestimonials`, `HomeFaq`) rather than fork. Only `site-*` tokens; the `landing-*`/`b2c-*` landing helpers are deleted.

## Deploy config
- `web/vercel.json` `git.deploymentEnabled` ends in `"**": false`, so every branch Vercel must build is listed by name: `main` (staging, the promote gate) and the branch `promote-web.yml` pushes (`production-web`). An unlisted branch is discarded with no build and no error: the promote just times out after 15 minutes (2026-10-25). `check:deploy-branches` enforces it; ci-web runs on `promote-web.yml` edits for that reason.

## Actions
- A row or header with more than one action offers at most one inline primary and the rest in `ActionMenu` (`@/foundation/ui`, the "⋯" menu; danger items last). Never three buttons side by side. `RowAction` icon buttons stay for a single action. `ActionMenu` is `PopupMenu fixed`, so table/card `overflow` cannot clip it.

## Landing `/` (rebuilt 2026-11)

- Composition is `domains/marketing/LandingPage.tsx`; copy in `marketing/landingCopy.ts`, captures in `home/landingShots.ts`. Numbers in copy come from `foundation/config/copyNumbers.ts`.
- Hero is a deep-blue band (`bg-site-deep`, `HeroPhrase className`, `HeroProof onDeep`) with a device frame of `LANDING_SHOTS.marked` hanging over its edge; `HowItWorks` (`#how`: a rising chart panel on xl+ (1280px, narrower clips the fixed-width callouts), a spine below; text and figures in `home/howItWorksData.ts`, vignettes in `HowItWorksVignettes.tsx`; it owns the 168/360px top padding the laptop hangs into, so `FeaturePanels` starts at 0), four tinted `FeaturePanels` (`site-tint-*` tokens), then `ExamCards`, the old `Pricing` (`section` prop), `HomeTestimonials tone="ground"`, `InstitutionsBand` (one line), `HomeFaq split` and `ClosingBand`, which the `SiteShell footer="card"` footer overlaps with a negative margin.
- Which exams show on `/` and in `ExamTabs` (and so `/pricing`) is `VISIBLE_EXAMS` in `pricingContent.ts`; `EXAMS`/`PRICES` data stays. The founders letter and feedback form are public routes `/founders` and `/feedback`, not home sections.
- A hero-overflow trap: a device base bar wider than the gutter (`-mx-10`) scrolled the page at 768; keep decorations inside the 20px gutter.
- Another owner's `next dev` can leave `.next/dev/types/*` truncated mid-write; `npm run types` then fails on generated files. Truncate the garbage tail (gitignored) rather than killing their server.
- `site-wave*` CSS stays: `AuthQuotePanel` uses it. Exam pages share Blocks, HomeFaq, HomePractice, HomeFounders, `foundersLetter`, `faqItems`.

- **Assess words live in `capabilities/assess-words`** (`useAssessWords`, `INSTITUTION_WORDS`, `EMPLOYER_WORDS`, `assessWordsFor(surface)`), not `domains/assess`. A node test imports `@/capabilities/assess-words/vocabulary`, never the barrel (it pulls TSX). A surface manifest may carry `refusal` (`screens`, `title`, `body(orgName)`): `app/app/[workspace]/screen.tsx` renders `RefusedScreen` for those screens before `notFound()`. Hire refuses practice and mock screens this way.
- **Hire copy is a pure function of the words**: `thing(args…, w: AssessWords)` with `w` last, required and never defaulted, an inline `w.hiring ? employer : institution` ternary, and the institution branch byte-identical to the text before hire existed, pinned by a literal test for both arms. No regex rewrites of prose, no keyed `hiring/institution` tables except where a whole record is overridden.
- The public site's gutter and 1280px cap live in one place, `SiteContainer` (foundation/ui/site): `Section`, `SiteNav` and `SiteFooter` use it so their edges line up. Do not hand-write `max-w-[1280px] px-*` in a marketing component.
- The landing hero's rotating phrase (`HeroPhrase`) is an allow-listed timer in `scripts/check-no-polling.mjs`; the h1 keeps an sr-only full sentence, and `e2e/public/layout.spec.ts` asserts its two lines never overflow at 320 to 1280.
- Landing, mobile: below `md` the hero shows a phone frame (`step-marked-mobile.png`, a real capture, 390x640 CSS px at dsf 2 = 780x1280 file; one art-directed `<picture>` shared with the laptop) instead of the laptop; `#how` below `xl` is a bare spine with no panel and owns the overlap padding. The footer card is `md+` only (two-column link grid below). The FAQ is one `max-w-3xl` column (no `split`).
- Hidden exams: CASC and Ortho are hidden through `VISIBLE_EXAMS` (cards, tabs, `FOOTER_EXAMS`) and `HIDDEN_EXAM_PATHS` (derived from `EXAM_LINKS`, in `siteLinks.ts`) (sitemap, noindex in `exams/[exam]/page.tsx`). Their pages stay reachable by URL; re-enable in those two lists. `visibleExams.test.ts` fails if a nav or footer link names them.
- Trap: a second `next dev` in one directory is refused; use `NEXT_DIST_DIR=.next-3102 ... -p 3102`, then `git checkout web/tsconfig.json` (it rewrites the include list).
