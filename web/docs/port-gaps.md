# Port gaps

Screens that came across from `frontend/` whose backend `platform-api` does not
serve yet, and the handful of places where the two systems disagree about a
shape. One file so the backlog is countable rather than scattered through
`TODO` comments nobody greps for.

Each entry says what the screen does today, so nothing is silently dropped.

## 2026-09-23 — a full re-check, and the two ways this file was wrong

Everything below was re-read against the current tree. This file's own rule is
"annotate, don't delete", so nothing here is removed — but a reader should know
that the register drifted in **both** directions, and that a row saying "not
ported" is now evidence to check rather than a fact to act on.

**It understated the work.** The whole of `gap-closure-plan.md` Phase 1 was
already implemented — the checkout return routes, `fetchLandingStats`, the public
blog rail, `POST /site/messages`, the exam-date countdown, extra reading time,
SSO discovery, `/me/attempts` in the mock station table, and the
station-comment dedupe. So were three rows that still read as open: there *is* a
platform-admin listing (`/platform/admins`, driving `/staff/team`), there *is* a
cross-tenant audit and an organisation member read wired into the staff console,
and the runner *does* show a reading brief (`sessions/SupervisorReadingBrief.tsx`
besides the candidate's `trainee/SlotReadingBrief.tsx`).

**It reported a security hole that is shut.** Phase 0's S1 — a trainee reading
`StationRead.content` with the patient brief in it — is implemented server-side:
`stations/service.py` takes `full_content` and reduces a non-staff reader's rows
through `candidate_content`. The `SelfPractice.readingBrief()` workaround is no
longer load-bearing. S3 was checked at the same time.

**It missed ten things outright**, found by auditing `frontend/` against
`platform-web` screen by screen rather than through this file. All ten are fixed
now, and are recorded here because they were never in the register:

| What was wrong | Where | Fixed by |
|---|---|---|
| The examiner's review screen never received an `attemptId`, so it derived zero scoreable domains from a null payload — **per-domain marking could not be done from the UI at all**. One caller link sent `?attempt=` that nothing read; the other sent nothing. | `app/[workspace]/slots/[slotId]/review/page.tsx`, `domains/assess/SlotReview.tsx` | The route forwards `searchParams.attempt`; the sitting report now carries `attempt_id` per station (platform-api) so `CandidateCard` can link with it; an absent attempt says so rather than rendering an empty rubric. |
| Every legacy session URL 404ed: `/b2b/<org>/sessions…` redirected to `/app/<org>/sessions`, but the route tree renamed the word to **sittings**. The repo's own test asserted the broken destination. | `foundation/routing/legacyRedirects.ts` | Table rewritten for the renamed sub-trees (`sessions`→`sittings`, a slot's `feedback` page→`review`, `[org]/templates`→Authoring's station-templates, `trainee/sessions`→`trainee/sittings`), with the test now reading `src/app` off disk and failing if any destination has no page behind it. |
| `/welcome`, `/feedbacks`, `/blogs` and the four console sign-ins redirected to routes that do not exist; `/b2b/trainee/join/<slotId>` read `join` as a workspace slug, so **emailed join links were dead**. | same | Same pass. Each now lands on a page that answers, or on the arm's `dashboard` where nothing does. |
| `must_change_password` was read by nobody. An account created by an invitation kept running on a password an administrator set. | `foundation/session/guards.tsx` | `RequireSession` sends a flagged account to `/change-password` and renders nothing until it is cleared. |
| **A partner arm could not invite anybody.** `screenNames` was `["dashboard","reporting"]`; a partner admin had no route to their own editors. | `surfaces/partner/surface.ts` | `team` added to the manifest, answering Assess's `Team` — the memberships are the same rows behind the same routes. |
| **A circuit could not be corrected.** `PUT /orgs/{slug}/circuits/{id}` was served and tested and had no caller, so "circuits are immutable" read as a backend limit. `edit-lock` was unwired for the same reason. | `domains/assess/sessions/api.ts` | New `EditCircuit` screen sharing one `CircuitBuilder` with the create form, pre-filled from the console and gated by `editable`/`edit_block`. |
| **Partner attribution was dead.** `middleware.ts` ported the redirects and dropped `proxy.ts`'s attribution half; `POST /growth/arrivals` and `/growth/acquisitions` had no caller, and sign-up carried nothing. BMJ reporting would have stopped accruing at cutover. | `middleware.ts`, `foundation/attribution/` | Visitor key minted first-touch at the edge, arrival recorded with `waitUntil`, and the key spent on the new account after `POST /auth/register`. The signed `osce_acquisition` cookie did not come across: platform-api asks for no signature, so there was nothing to sign. |
| **Analytics, consent, SEO and the sitemap had no new home.** `CookiesConsentModal` was ported and never rendered; no gtag; no `openGraph` although `og-image.png` shipped; no `robots.txt`/`sitemap.xml` (`next-sitemap` was dropped with no replacement) while the privacy policy still claimed Mixpanel. | `foundation/analytics/`, `app/metadata.ts`, `app/robots.ts`, `app/sitemap.ts` | Consent gates gtag as the old client did, on the same `analytics-consent` key. Metadata ported from `frontend/src/app/metadata.ts` minus two lines that were already broken there (a `manifest.json` that never existed, and the `appleWebApp.capable` beside it). The public path list is shared with the robots file so the two cannot disagree about what is private. |
| **`platform-web` was not self-contained.** Thirteen files imported `@/b2b/**` and `@/shared/**` out of the retiring tree, so deleting `frontend/` broke the build — and the alias hid half the ported code from every grep run against this project. | `next.config.ts`, `tsconfig.json` | The 63-file closure (template builder, station structures, the four arm v1 templates, validators, the shared primitives) moved to `capabilities/authoring/structure`. The `@/b2b` and `@/shared` aliases and the `prebuild` that installed the old tree's dependencies are gone; `npm run build` proves it. |
| Four backend routes were served, typed, and called by nothing: `POST /auth/sso/login` + `/callback` (the sign-in button said "not available yet" against a live door), `/cv`, `GET /platform/site/messages`, and `POST /platform/generate/station`. | `capabilities/account/`, `domains/platform/`, `capabilities/authoring/` | The SSO button now redirects and `/auth/sso/callback` closes the loop; the Ortho CV upload and its twelve sections are back on the profile; `/staff/messages` is the inbox; a station can be generated from a prompt with no template, which `CreateStation` always allowed and the create screen forbade. |

`GET /station-generation-profiles` looked like a fifth orphan and is not one —
it was wired all along, inside the tree only reachable through the alias. That
is worth stating because it is the same grep that produced the other four.

## Five of these are now served

The backend jobs B2 and B3 closed a row of these (platform-api commits c04411e
and b1c597d). The entries below are **left standing with a note** rather than
deleted, because what a screen does today is still what it does until somebody
wires the new route:

- **Landing statistics** — `GET /site/statistics` exists, cached for ten
  minutes and carrying `as_of`. **Wired 2026-09-21**: `fetchLandingStats()`
  reads it through `domains/marketing/api.ts` and the numbers band and the
  hero's social proof render again. One figure has no counter of its own —
  see the "Landing statistics band" row below.
- **Public blog listing** — `GET /media` and `GET /media/{slug}` no longer
  require a bearer. **Wired 2026-09-21**: `landingBlogs.ts` asks again,
  signed out included, and the landing's blog rail renders.
- **Messages / contact** and **product feedback** — `POST /site/messages` takes
  both, with a platform-admin inbox behind it. **Wired 2026-09-21**: the
  "Help Us Improve" section is back in `landingSections`, and the old
  `/messages` screen is ported to `capabilities/help/Messages.tsx` at
  `/app/<workspace>/messages` (the redirect table already pointed there).
- **Accessibility (extra reading time)** — `users.extra_reading_percent` is on
  `/me`. It is a person's own practice arrangement and is **not** applied to a
  circuit's clock, which serves everybody on it.
- **Exam wishes / the dashboard countdown** — `users.exam_date` is on `/me`.

Still genuinely absent: **achievements**, **photo upload**, **push
notifications**, **public user profiles** and **blog authoring**. SSO was on this
list and is not any more — both halves of it landed on 2026-09-23; see the row
below.

## No endpoint on platform-api

| What | Where | Today |
|---|---|---|
| Landing statistics band | `domains/marketing/Numbers.tsx` | **Wired 2026-09-21; stopgap closed.** `fetchLandingStats` reads `GET /site/statistics` through `domains/marketing/api.ts`, and the band and the hero's social proof render again. The band's fourth card ("AI feedback reports generated") read the retiring backend's `all_feedback`; the consultation stand-in that replaced it is gone — `SiteStatistics` now carries a dedicated `feedback` counter (evaluated attempts) and the card shows its own number. |
| Achievements | `capabilities/account/Achievements.tsx` | **Ported as its own empty state, and it asks for nothing.** The old screen counted station badges from `user.station_progress` and computed streaks in the browser from the transcript list; `platform-api` has neither — progress is attempts, and a streak exists nowhere on the backend. The component takes the four numbers as props and defaults them to zero, so the day something serves them it is a one-line change at the call site rather than a port. It has no route: see "Route files the account capability still needs". |
| Messages / contact | `capabilities/help/Messages.tsx` | **Ported 2026-09-21.** The old `/messages` screen — "Contact & Feedback", two tabs — is a straight port over `POST /site/messages` (`kind: "contact"`), at `/app/<workspace>/messages` through its own `messages` capability, which puts "Contact & Feedback" back in the consumer sidebar ahead of Community; the redirect table already sent `/messages` there. One adaptation: the old screen widened when the help dock expanded, read off a context the shell owned; the shells here keep that state private, so the width is the fixed `max-w-2xl` every sibling port settled on. |
| Product feedback form | `domains/marketing/sections/LandingFeedbackSection.tsx` | **Wired 2026-09-21.** The "Help Us Improve" section is back in `landingSections` with the retiring landing's two-tab widget ("Harsh Truth" / "Feature Wishlist") ported as it was, posting `kind: "product_feedback"` to `POST /site/messages`. The signed-in product-feedback form (stars, testimonial question) is ported beside the contact tab in `capabilities/help/ProductFeedbackForm.tsx`. |
| Push notifications | not ported | `web-push` is deliberately not a dependency here yet. |
| SSO configuration | `capabilities/account/Login.tsx` | **Discovery wired 2026-09-21.** The sign-in page asks `GET /auth/sso/sign-in?host=<this host>` on mount (`readSsoSignIn` in the account capability's `api.ts`); a host nobody has claimed answers 404 and the ordinary password form stands. On an answer the organisation's button renders with the backend's `sign_in_label`, and on `sso_only` the password form is not drawn — a display rule only, nothing refuses a password login. **The button is not a door**: `/auth/sso/login` does not exist (the sign-in half — who verifies the identity — is still open decision S-1), so clicking it says organisation sign-in is not available yet and points at support **[2026-09-23: the button is a door now.]** `POST /auth/sso/login` and `/auth/sso/callback` are served, and `startSsoSignIn`/`completeSsoSignIn` in the account capability's `api.ts` use them: the button redirects to the broker's URL and `app/(auth)/auth/sso/callback/page.tsx` posts the token it was handed and adopts the session. Decision S-1 is closed. The token is verified by the backend, never decoded here. |
| Public user profiles | not ported | `/users/[userId]`. The old `b2c/components/shared/users` was not a public profile at all: it is an **administrator's** user list and user detail — plan editing, station-progress resetting, hard delete, filters by plan type. None of it is servable. See "The old `users/` folder" below. |
| Blog authoring | not ported | Reading is `capabilities/media`; authoring has no endpoint. |
| Public blog listing | `domains/marketing/support/landingBlogs.ts` | **Wired 2026-09-21.** `GET /media` is public, so the rail asks again — signed-out visitors included — and links each card by the item's slug. |
| Exam wishes | `capabilities/account/ExamWishes.tsx` | Ported, and nothing renders it. It was shown in the week of somebody's exam, and `UserRead` carries no `exam_date` — the same gap the dashboard countdown hits. |
| Accessibility settings (extra reading time) | `foundation/ui/Timer.tsx` | The old client read `accessibility.needs_extra_reading_time` off the user and extended the clock from inside the timer. No such field on `platform-api`. The timer takes the duration it is given; when the field exists, whoever creates the attempt applies it. |
| Photo upload | `foundation/ui/PhotoUpload.tsx` | Posted to the old backend's `/api/upload_photos/{id}`. The component takes an `upload` function now, and nothing supplies one yet. |

## The station library

Four things the retiring station screens did that `platform-api` has no answer
for. The first row used to be the biggest of them and is now served.

| What | Where | Today |
|---|---|---|
| The candidate brief, patient information and management plan | `capabilities/attempt-runner/material/` | **Served.** `LibraryStationRead` still carries no `content` — the library is browsable by every signed-in user and the content is the brief and the marking guidance — but a candidate reads their own station through their *attempt*: `GET /attempts/{id}/brief` from the moment it is created, and `GET /attempts/{id}/review` once the consultation is over. How the patient is played (persona, opening line, expanded history) and the examiner's context never leave the server at all. |
| `GET /api/v1/stations/{station_id}` | `findLibraryStation` in `capabilities/stations/api.ts` | There is no per-station read for a learner — every one of them is an authoring route under `/orgs/{slug}/…` or `/platform/…`, gated on permissions a candidate does not have. A station opened by link is found by walking the browse list, bounded at twenty pages. It works and it is cheap, because a row is a title and two ids, but a shared link to a station beyond that is a "we could not find that station". |
| Searching the library | `useStationLibrary.ts` | `browse_library` takes `exam_code`, `cursor` and `limit`. The search box filters what has been paged in, which is why "Load more" stays offered while a term is typed. A `q` on the endpoint would make it a real search. |
| Flagging a station | `StationHeader` + `POST /me/station-flags` | The runner shows the flag control again. The route accepts a report today; persisting flags for the content team and returning them on `/me` is still open. |
| Attempts used, out of the exam's limit | **Served for a session's station.** | `EntryRead.attempts` and `ExamRead.station_attempt_limit` are the pill's two halves, and the station screen shows them. Free practice from the library has no counter, because the limit is counted per set entry and a library station is not one. |
| Live marking during a consultation | not ported | `live/LiveCoveragePanel.tsx` and `LiveCoverageFeed.tsx` subscribed to `/api/live-coverage-stream` and showed competencies as they were covered. `GET /api/v1/attempts/{id}/stream` pushes `AttemptRead` snapshots until the attempt is marked — the right stream, without the coverage frames. Adding a `coverage` event to it is what this needs; the feed is worth bringing back, because it is the one thing in the old runner people asked for by name. |
| Station photos on legacy hosts | `material/StationBrief.tsx` | Rendered with a plain `<img>` rather than `next/image`. The URLs are absolute, on hosts this app does not configure, and an unconfigured host is a build-time error in `next/image` rather than a slow picture. Adding `remotePatterns` for the image hosts would let it back. |

## Shape disagreements — station comments

`POST /api/v1/stations/{id}/comments` takes an `audience`, which is an
organisation **id**. A capability is given `orgSlug` by the surface context and
deliberately nothing richer, so `StationComments` takes the id as a prop the
way `Discussion` does — the arm supplies it, as `domains/assess/OrgDiscussion`
already shows. Mounted with no prop, as the shared `/stations` route mounts it
today, a comment is public. An institution wanting its own thread is a
four-line wrapper in `domains/assess`, not a change here.

`PostRead` carries `author_id` and no display name, so a comment shows its date
and its likes and not who wrote it. The old station comments showed a username.

## Study material

One capability over four old folders — slide decks, the A-to-Z, articles and
podcast episodes are one `media` row with a `kind` here. These are the places
where that row carries less than the four old collections did.

| What | Where | Today |
|---|---|---|
| A specialty facet | `SummaryIndex.tsx`, the deck sidebar in `DeckView.tsx` | `MediaRead` has no specialty or tag column. The old slides list filtered on `?specialty=` and every summary carried a `specialties[]` the A-to-Z grouped by. `specialtiesOf` reads `content.specialties` (or `content.specialty`) from the authoring payload instead, and both facets hide themselves when nothing carries one — so the Specialty tab is an empty state, not a bucket holding the whole library. A column, or a tags table, is what this wants. |
| Filtering the library by exam | `MediaLibrary.tsx` | `GET /api/v1/media` takes `kind` and nothing else. Every old list was implicitly scoped to the signed-in person's `app_type`, so a PLAB candidate never saw CASC material. Items carry `exam_code` and the card shows it as a badge; everything is listed to everybody until the endpoint takes an exam. |
| Searching inside a kind, and a snippet per hit | `MediaSearchResults.tsx` | `GET /api/v1/media-search` is one vector search over every kind and returns `id`, `kind`, `slug`, `title` and a score — no excerpt, no `kind` filter, no paging (`next_cursor` is always null). The old A-to-Z and blog boxes were server-side substring matches over one collection each and returned whole rows, which is what let them show a preview. It also answers nothing at all on a deployment with no embedding key, by design — a local API with no key looks like a library where nothing matches. |
| A total, for paging | `PagedGrid` in `MediaLibrary.tsx` | Cursor pagination with no `total_count`, so there is no page count until every page has been walked. The library walks the cursor (six pages of a hundred, which the A-to-Z needs anyway) and pages in the browser. A library past six hundred items needs a real page. |
| `updated_at` on an item | `ArticleView.tsx` | The old article header printed "Published … · Updated …". `MediaRead` carries `published_at` only, so the Updated line is gone. |
| Audio for an episode | `EpisodeView.tsx`, the Listen button on a summary | A `podcast` item plays only what `content.audio_url` (or `content.podcast_url` on a summary) points at, and nothing uploads one — there is no media asset endpoint. The seeded episode has no audio and the player says so. |
| The upgrade path on a locked read | not ported | The old A-to-Z answered `403` with `show_upgrade_modal` for an unsubscribed reader and offered "Upgrade to Pro" in place of the list. `GET /api/v1/media` gates nothing today (its own tests pin that search is deliberately unfiltered by what a reader has bought), and `/billing/checkout` is unwired — see J8. When the read becomes entitlement-gated, this screen needs that prompt back. |
| Blog authoring, and a public listing | not ported | Covered above: reading is this capability, authoring has no endpoint, and an anonymous read would also bring back the landing's blog rail. |

Two things from the old folders are deliberately elsewhere. `shared/media/` is
`MicrophoneCheck` — a pre-flight for the consultation runner, not study
material, and it belongs to the station library (J3). The "Conversation" tab on
a deck never had a backend in the old client either; it is kept, and still says
there is no conversation.

## Community — what the posts table does not carry

The discussion screens (`capabilities/community`) came across whole: the three
tabs, the composer, a question and its answers, likes, the author's own delete,
and the comments under a station. These are the places the old screens knew
something `platform-api` does not.

| What | Where | Today |
|---|---|---|
| A display name on a post | `posts.tsx`, `authorLabel` | `PostRead` carries `author_id` and nothing else, so only the viewer's own posts can be bylined. A stranger reads as "@a colleague" where the old screens read "@somebody". One `author_name` on `PostRead` fixes every screen here at once — it is the single most visible gap in this capability. |
| `GET /community/questions/{id}` | `QuestionDetail.tsx` | There is no read for one question; only the paged list and the replies. A thread is found in the page the feed already serves, so a question older than the first hundred opens as "Question not found." The same shape as `findLibraryStation`, and the same fix. |
| Questions I asked | `MyQuestions.tsx` | No `mine` or `author_id` filter on the feed, so the tab narrows the first page (100) to the viewer. Bounded, and therefore honest, but somebody with a long history sees only their recent questions. |
| Answers I wrote | `MyAnswers.tsx` | Nothing lists one person's replies — replies are read per question, so assembling the tab means a request per question in the feed. The screen keeps its empty state rather than being built on a hundred requests. A `GET /community/replies?author=me` is the whole of what it needs. |
| Tags on a question | not ported | The old composer offered `MEDICAL_SPECIALTIES_CATEGORIES` as chips and the cards showed them back. `posts` has no tags. `exam_code` is the nearest thing the table has and `PostRead` does not return it, so tagging would write something nobody could read. |
| Images on a post | not ported | The old question, reply and answer forms all carried an `images` array, always posted empty because the upload endpoint went with the retiring backend (see *Photo upload*). Nothing is lost that was working. |

`POST /stations/{id}/comments` with a station id that does not exist answers
`internal_error` rather than `station_not_found`; the row is written against a
foreign key and the failure is not mapped. Nothing reaches it through the UI.

**Two implementations of the station comments.** `capabilities/stations`
carries its own `listStationComments` / `commentOnStation` and a rebuilt
`StationComments`; `capabilities/community` now carries the port of the old
screen — the real copy, the like toggle, the author's delete and the
moderation footnote — beside the questions it shares a table with. One should
go, and it should be the rebuild: a capability may import another capability,
so `capabilities/stations` swapping its import for
`@/capabilities/community` is a one-line change. Until it happens the station
detail screen shows the rebuilt panel.

**Scoping needs no wrapper any more.** `useRoom()` turns the workspace slug
from `useSurface()` into the organisation's id using the memberships the
session already carries, so `Discussion` scopes itself on whichever workspace
it is mounted in. `domains/assess/OrgDiscussion` still works — the `orgId` prop
it passes wins — but nothing has to supply one.



## The one that blocks a whole screen

**Consumer performance analytics.** The four exam dashboards draw three things
from the retiring backend's `/api/{exam}_dashboard`: a pass/fail/critical
summary, a score per rubric domain, and a trend line over time.
`GET /api/v1/me/dashboard` serves none of them — it serves entitlements,
attempt counts, recent attempts and station sets, which is a real dashboard but
not that one.

The data exists. `assessment_results.payload` holds the engine's structured
output, keyed on the rubric's own domain and competency ids, and
`reviews/scoring.py` already turns a flat `domain.skill.score` map into a score
per domain — that is how an institution ranks a cohort. What is missing is the
step between: reading a framework's payload into that flat form. The
institution path never needed it, because its RAG comes from human reviews.

So the endpoint is buildable and contained — a `/me/performance` in the
`dashboard` slice, reading `attempts` and `rubrics` the way `service.py`
already reads `entitlements` and `station_sets` — but it needs a real marked
attempt to write against, not a guess at the payload's shape.

The endpoint is being built now (job B1). `domains/train/dashboard` is written
against its agreed shape — `{ exam_code, summary: { pass_rate, fail_rate,
critical_rate }, domains: [{ id, label, score }], trend: [{ date, score }] }` —
and `readPerformance` treats a 404 as "nothing to draw yet" rather than a
failure, so the screen renders the charts' own empty states today and fills in
when the route lands. Every other status still raises and still shows an error
with a retry.

Until then the consumer dashboard shows what is true: progress, recent
attempts, sets and access.

### What `/me/performance` still will not cover

Four things the old dashboards drew have no source on the platform at all, and
the ported screen leaves them out rather than inventing them.

| What | Old source | Today |
|---|---|---|
| SCA's RAG mix by domain and its category volume chart | `/api/dashboard/rag_by_domain`, `rag_by_category` | Those charts needed a count of red, amber and green marks per domain. `/me/performance` carries one score per domain, so SCA draws the same `ThresholdBars` every other exam does, and `RagCompositionBars` / `CategoryVolumeChart` are unused by this screen. The competency hero keeps the RAG picture, from the summary's three rates. |
| SCA's "What to work on" insights, and the "Practise these three with Athena" link | `/api/dashboard/actionable_feedback` | `InsightsList` renders its own "No insights yet" state and takes its items as a prop, so wiring it later is one call site. The Athena chat the link opened is the assistant capability's, not the dashboard's. |
| SCA's Trends tab (skill movements) | the `trends` half of `actionable_feedback` | Not ported. There is nothing to put in the tab, so the tab is gone rather than empty. |
| Exam date, and the countdown in SCA's header | `user.exam_date` on the retiring backend | No such field on `platform-api`'s `/me`, so the "Add exam date" control and the "6 weeks until your exam" line are not there. A small field on the user, or a per-exam target date, brings both back. |

`critical_rate` is served but is only drawn in SCA's competency hero, as the
amber band. The old PLAB and CASC screens defined a colour for it and never
showed it either.

### The active exam — closed

**Was:** the old client got its exam from the subdomain, so there was one exam
per session and no picker anywhere in the product. The platform had no such
field, so four screens each derived their own answer from a different source —
the dashboard from what had been attempted, the station library from the whole
published catalogue, peer practice and the mock form from whichever exam sorted
first — and each offered its own dropdown over exams nobody had bought.

**Now:** `users.exam_code` is recorded at sign-up (the per-exam landing pages
carry it into the register form) and `GET /me/dashboard` answers `exam_codes`
and `current_exam_code` — live entitlements plus that exam, filtered through the
published catalogue. `foundation/session/useCurrentExam` is the one reader, and
the choice is remembered per person in `localStorage`.

Every per-screen selector is gone. The only switcher left is the navigation's
footer line (`SCA · 3 weeks to exam`), and it appears only for somebody holding
more than one exam — which almost nobody does.

`GET /api/v1/stations` refuses an exam the caller may not open, so the chips
that used to sit above the library would have been buttons that mostly 403.

## Mocks (practice sessions)

Six things the retiring mocks screens did that `platform-api` has no answer
for, and three places the two systems disagree about what a session is.

| What | Where | Today |
|---|---|---|
| Deleting a session | `domains/train/mocks/MockSessions.tsx` | The old card had a bin next to its title (`DELETE /api/delete_mock/{mock}/{user}`). There is no `DELETE /me/station-sets/{id}`, so the card has no bin. A session is cheap and locks rather than disappearing when access lapses, so this is the least painful of the six — but somebody with fifty sessions has no way to tidy them, and `scripts/smoke.mjs` leaves a "Smoke session" behind on every run for the same reason. |
| Editing a session | not ported | `UpdateMock.tsx` renamed a session and added or removed its stations (`PUT /api/update_mock/{id}`). `/me/station-sets` serves `GET` and `POST` and nothing else, so a session is immutable once created and the pencil is gone from the card with the bin. The screen is a straight port the day a `PATCH` exists. |
| Listing a station's previous attempts | `domains/train/mocks/MockStationsTable.tsx` | The expander under each station showed "All previous Transcripts (3)" and "All previous Feedbacks (2)", linking to `/transcripts` and `/feedbacks` filtered by station. `EntryRead` carries a count of attempts and the date of the last one, but no attempt **ids**, and there is no `GET /me/attempts`, so there is nothing to count and nothing to link to. The row still opens and still shows the two empty states. A listing filtered by set entry is what this needs. |
| "Review Last Attempt" | `domains/train/mocks/MockStationsTable.tsx` | Same cause: no attempt id to review. The act it stood for — go back over the station you sat — is served by `POST /me/station-sets/{set}/entries/{entry}/debriefs`, so the button is wired to that and reads "Talk Through Last Attempt". When an attempt listing exists, the old link belongs beside it rather than instead of it. |
| "Feedback" badge on a session card | `domains/train/mocks/model.ts` | The old list read a `has_feedback` the retiring backend wrote onto the mock, and used it to turn "Start" into "Review". `SetRead` has no such field. `sessionAction` branches on `locked` and `completed_at` instead, which agrees with the old behaviour everywhere except a session whose marking is still running — that reads "Start" for a few minutes longer than it used to. |
| The exam-date prompt | not ported | `CustomizeMock` opened a modal asking for the candidate's exam date on first visit. `UserRead` carries no `exam_date` — the same gap the dashboard's countdown hits — so the modal is not there. |

### Shape disagreements

**A session's stations are chosen in the browser.** `POST /api/customise_mock`
took a number of stations and picked them server-side; `POST /me/station-sets`
takes explicit `station_version_ids`. The Setup tab keeps the question the
candidate knows — "how many stations?" — and `chooseStations` in
`domains/train/mocks/model.ts` samples the library, preferring versions this
person has not attempted. That is better than it sounds: the client already
holds every set with every entry's attempt count, so the exclusion is exact and
needs no per-user state on the backend.

**A session has no stored duration.** The old mock document carried a
`duration` written at create time, and eight constants in the old
`constants.ts` (`SCA_DOCTOR_TIMER_DURATION` and siblings) told the rules screen
what a station's clock was. `sessionMinutes` derives it from
`ExamRead.default_reading_seconds` and `default_simulation_seconds`, so a
session created before an exam's timings changed stops advertising the old
length. `station_attempt_limit` replaces the hardcoded
`ALLOWED_STATION_ATTEMPTS = 3` the same way.

**One route, not five.** The retiring client spread this over `/mocks`,
`/mocks/list`, `/mocks/[id]`, `/mocks/[id]/update` and
`/mocks/[id]/complete`. There are three routes here, so the sessions list is
the third tab of `/mocks` rather than its own page, and the completion screen
is a state of the session — `set.completed_at` — rather than a URL you could
reload into congratulations for work finished last week. `update` has no
backend (above) and needs no route.

`MockCore`'s other two tabs are somebody else's work rather than gaps:
"Consultation Tips" is the help capability's content and "Flagged Stations"
belongs with the station library, which has its own flagging gap above.

## Feedback, transcripts and debriefs

The screens are ported and the marking and the transcript are served. What the
backend does not have is a way to *list* any of it, and a debrief that is not
about a mock's station.

**Attempt history — served.** `GET /me/attempts` is the paged listing three
screens were doing without, and each row names its station. It answers "every
time I have sat this one" for the transcript picker and the feedback history,
and "how many has this entry produced" for the session's station table, which
had hard-coded "No transcripts yet" for the whole port.

**Debriefs are readable only through the tutor's memory.** There is no
`GET /debriefs/{id}` and no debriefs collection: `DebriefSummaryRead` reaches a
client only inside `GET /me/tutor-memory`, so `DebriefDetail` reads the list
and finds its id in it. Two consequences worth stating — a debrief page costs
the whole memory, and the route is `/me/…`, so an examiner cannot read a
trainee's debrief even though the debrief capability is mounted on Assess. A
`GET /attempts/{id}/debrief` keyed on the attempt, with the same visibility
rule the result already has, would fix both.

**Mock debrief — served.** `POST /me/station-sets/{set}/entries/{entry}/debriefs`
is wired on platform-api and on the station feedback step (`DebriefChooseModal`).

**Library debrief — still open.** Free practice has no set entry, so the
feedback step explains that `POST /attempts/{id}/debriefs` is needed before
Start Debrief works there too.

**Feedback-ready notification — partially served (see `capabilities/pending-feedback`).** The retiring client
kept a shell-level watcher (`PendingFeedbackContext` and an SSE hook) so a
toast found you wherever you were when a marking landed. The station screen
polls while its marking modal is open and the session-complete screen re-reads
statuses, which covers the two moments somebody is actually waiting — but walk
away mid-marking and nothing tells you. `GET /attempts/{id}/stream` is the
event; what is missing is something above the arms listening to it.

**An examiner cannot yet read a candidate's attempt.** `FeedbackView`,
`AttemptFeedback` and `TranscriptView` ask nothing about who is reading — that
is the point of them being capabilities — but `GET /attempts/{id}/result` and
`/transcript` are owner-or-platform-admin (`service_reads._ensure_visible`),
and the reviews slice has no transcript read of its own. So the screens are
ready for the examiner and the endpoint is not: a GP lead reviewing a slot can
see their org's reviews but not the machine's mark or the words that produced
it. Widening the visibility rule to a member of the organisation the attempt's
slot belongs to is the whole of it.

**"Practice as Patient" is wired through assistant voice, with limited script
detail.** The retiring debrief modal offered a second choice beside the
debrief: run the same case from the patient's side with Athena as the doctor.
Platform-web now starts this as an assistant session (`athena-doctor`) and uses
the assistant `voice-token`, not a debrief attempt. The left script panel uses
the already-loaded attempt brief plus `GET /attempts/{id}/review`, so station
patient information, biodata and ICE are available. `PatientReviewRead`
intentionally does not expose the hidden actor history, opening sentence or
persona. Full History/Persona parity needs a dedicated owner-safe
roleplay-script read if product wants that shown after the attempt.

## Shape disagreements

| What | Where | How it is handled |
|---|---|---|
| `GET /attempts/{id}/result` is a page | `capabilities/feedback/api.ts` | The endpoint answers `Page[AssessmentResultRead]`, not one result: re-scoring under a new policy writes beside the old so a candidate's history stays readable, and the items come back oldest first. `attempt-runner/api.ts`'s `readResult` is typed as a single `AssessmentResultRead` and would read `.payload` off the page — the feedback capability reads the page itself and shows the last item, with a picker when there is more than one. |
| `AttemptKind` in `attempt-runner/api.ts` | `capabilities/attempt-runner` | The client spells the kinds `set_entry` and `slot` where the backend's `attempts.Kind` is `set_station` and `exam_slot`; `practice`, `self_practice`, `debrief` and `peer` agree. Only the first two are wrong now — `self_practice` was missing from the union until the institution's self practice needed it, and that is the one kind this union is actually used to *send*, because `POST /attempts` accepts `^(practice\|self_practice)$` and nothing else. The rest are created by their own routes, so the union describes them rather than asking for them. `capabilities/transcripts/api.ts` labels attempts from the backend's spelling. |
| `user.user_id`, `user.station_progress` | `domains/marketing/InstallPrompt.tsx` | The old consumer user object inlined a progress array. The platform's `/me` carries neither — progress is its own endpoint. The prompt passes `user.id` and a count of 0, which errs towards showing onboarding once more rather than never. |

## The account capability

`capabilities/account` is the person rather than the work, mounted on all five
arms. Most of it is wired; these are the parts of the retiring screens that
`platform-api` has no answer for.

### Reads and writes the backend does not serve

| What | The old screen | Today |
|---|---|---|
| Editing your own name | `settings/profile/Profile.tsx` had an editable username and an "Update Profile" button | `/api/v1/me` is **read-only** — there is no `PUT` or `PATCH`. The name and the email are rendered as disabled fields. A box that discards what you typed is worse than a box you cannot type in. |
| Deleting your own account | The "Danger zone" card, `DELETE /api/soft_delete_user/{email}` | No endpoint. The card is not ported; nothing on the screen implies you can leave. |
| Preferences | `settings/preferences/SettingsPreferences.tsx` — AI training consent, extra reading time, "email me when a colleague is waiting", replaying the Athena onboarding | **None of these four fields exist on `platform-api`.** `UserRead` is id, email, name, `is_platform_admin`, `must_change_password` and memberships. The whole tab is left out rather than rendered with checkboxes that cannot save. It needs a `preferences` object on the user and a write for it. |
| The Exam tab | `settings/exam/SettingsExam.tsx` — exam type and exam date | An account is not bound to one exam any more; entitlements carry exam codes and are shown on the Access tab. The exam **date** has no field (the same gap the dashboard countdown hits). |
| Bank details for referral payouts | `settings/referrals/user/BankDetails.tsx` (293 lines) | The growth slice tracks a code, a redemption count and pence earned. There is nowhere to store a sort code, and nothing pays anybody out. Not ported. |
| Referral history per referee | `settings/referrals/user/ReferralHistory.tsx`, `ReferralDetail.tsx` | `GET /me/referrals` answers one `ReferralRead` — `{code, redeemed_count, earned_pence}` — with no per-referee rows, no join dates and no payout status. The screen shows the two totals it can prove. A listing endpoint would bring the table back unchanged. |
| The admin referral console | `settings/referrals/admin/*` (665 lines) | Marking payouts paid across all users. No endpoint, and it belongs to the staff console (J15) rather than to an account capability, since it is about other people. |
| Ortho CV upload and display | `Profile.tsx`, `/api/ortho/cv_status` | An exam-specific attachment on a consumer profile. No endpoint **[2026-09-23: ported.]** `/cv` and `/cv/{id}` are served and now have a caller — `capabilities/account/settings/CvPanel.tsx`, on the Profile tab for anybody holding `ortho`, polling while a row is `processing`. The `StructuredCv` sections are the twelve the old screen showed. |

### Checkout works; two things about it are worth knowing

`POST /api/v1/billing/checkout` is wired
(`capabilities/account/settings/PlanPicker.tsx`) and is now the only way
anybody buys anything. It sends a **plan code** and nothing else, and the
plans, prices and durations come from `GET /billing/plans` rather than from
constants in the bundle — the retiring client posted the pence it had rendered
and the backend matched them against a hardcoded table, so a price change broke
the purchase *after* the card was charged.

- **It needs Stripe configured.** With an empty `STRIPE_SECRET_KEY` the route
  answers `checkout_failed` before it even looks the plan up, because the
  adapter is a FastAPI dependency. The screen says so, and says no money left
  your account.
- **A migrated database has no plans.** `scripts/seed_platform.py` seeds no
  `plans` rows, so `/billing/plans` is empty and the Payments card explains
  that nothing is on sale rather than rendering an empty list.

`@stripe/stripe-js` is **not** needed and is not installed: the backend returns
a hosted `checkout_url` and the browser is handed to it. Nothing about a card
passes through this app.

### Route files the account capability still needs

Four route files, all outside `capabilities/`, for components that are built
and exported from `capabilities/account`:

| Route file | Component | Why it is where it is |
|---|---|---|
| `src/app/billing/complete/page.tsx` | `PaymentReturn` | **Done — the route file exists.** The backend hardcodes `success_url = {FRONTEND_URL}/billing/complete?session_id=…` in `billing/service_checkout.py`. **Not** `/payments/success`, which is what the retiring client used. |
| `src/app/pricing/page.tsx` | `CheckoutCancelled` | **Done — the route file exists** at `src/app/(public)/pricing/page.tsx`, which is `/pricing` (the group segment is not part of the URL). The same file hardcodes `cancel_url = {FRONTEND_URL}/pricing`. **Not** `/payments/cancel`. |
| `src/app/app/[workspace]/achievements/page.tsx` | `Achievements` | The old `/achievements` route. |
| `src/app/staff/settings/page.tsx` | `Settings` | **Done.** The staff console is outside the workspace grammar and has its own route tree, so `surfaces: ["…", "platform"]` on the capability does not reach it by itself and the route file is written out. The nav entry needed nothing: `SurfaceShell` appends `capabilitiesFor(manifest.id, …)` to every arm's own items, so Settings and Authoring appear on `/staff` from the capability registry. Checked in a browser against a live API in J15. |

### The old `users/` folder is the staff console — and is now served

`b2c/components/shared/users` (1,395 lines) was an administrator looking at
somebody else: a per-exam list with plan-type facets, and a detail screen that
edited another person's plan dates, flipped `has_paid`, reset a station's
attempt counter and deleted a station from their history.

**2026-09-19: ported to `domains/platform` as the account directory and the
account detail's Profile, Stations and Account tabs.** The columns and filters
are served by `GET /platform/directory` and `…/directory/summary` (dashboard
slice — every column is a different slice's fact, and `tenancy` sits below
four of them), the two station actions by `POST /platform/users/{id}/stations/
{station_id}/reset-attempts` and `…/delete-progress` (station_sets slice, which
owns the counter the old console reset). Both are audited. What the old
screen's flags meant is now read from what happened — a payment, a live grant,
a live sign-in — rather than flipped by hand, so Paid / Unpaid and Active /
Inactive are not buttons here: the acts are on Billing and Entitlements.

Still not there, and recorded so it is not mistaken for dropped:

| What | Today |
|---|---|
| Hard delete of an account, and the bulk delete (which the old list had disabled) | No delete; deactivation is the off switch. See "Deleting a tenant is gone" for the reason. |
| The "completed" tick per station | No such flag; a station is done when an attempt is `evaluated`, which the row shows. |
| Flagged stations | No `flagged_stations` on the platform — the same gap "Flagging a station" records above. |
| Referral code and earnings on the detail | `GET /me/referrals` is a person's own read; no console read of it. |
| Terms-of-service agreement date | Not recorded on `platform-api`. |
| The prev / next user pager | Fetched a thousand users to index into; not ported. |
| Booked mocks | Not a platform concept. |

### `domains/train/Access.tsx` reads receipts wrongly

Outside this capability and left alone, but found while wiring the same
endpoint. `GET /me/receipts` answers `Page[str]` — a page of receipt **ids** —
and `Access.tsx` maps over `data.items` reading `receipt.plan_label`,
`receipt.amount_total` and `receipt.currency` off each one. Every field is
`undefined`, so the card renders blank rows for anybody who has ever paid.
`capabilities/account/api.ts#listReceipts` shows the shape: list the ids, then
read each. Its `Receipt` type alias is wrong for the same reason.

The detail's date and money fields are **display strings** the backend has
already formatted (`"16 September 2026"`, `"£99.00"`), pinned by a receipt
oracle against the legacy formatter. They must be printed verbatim;
`new Date("16 September 2026")` is invalid on most browsers, and reformatting
a financial figure makes the screen disagree with the printed document.

## Deliberately not ported

- `confetti-check`, a developer scratch page.
- `features/[featureId]`, superseded by the landing's feature sections.
- The four separate B2B console logins (`b2bLoginRoutes`), replaced by the one
  sign-in the platform actually has.

## Authoring

`capabilities/authoring` is one implementation for three arms: the scope is the
base path (`/api/v1/orgs/{slug}` or `/api/v1/platform`) and nothing in the
capability branches on which arm is asking. Most of what is missing below is a
consequence of that — the backend serves the two scopes *almost* symmetrically,
and the three asymmetries are named in `api/scope.ts` rather than discovered at
runtime.

### The platform scope is narrower than an organisation's

| What | Where | Today |
|---|---|---|
| Reading brief | `sections/BriefEditor.tsx` | `PATCH …/stations/{id}/versions/{v}/brief` exists under `/orgs/{slug}` and not under `/platform`. The brief editor is offered when `supportsBrief(scope)` holds, so a staff author has to cut a new version to fix a typo in a brief. The endpoint is the same service call; only the platform router is missing it. |
| Throwing a draft away | `sections/StationDetail.tsx` | Same shape: `DELETE …/stations/{id}/versions/{v}` is org-only. The staff console archives instead, which is the safe half of the pair but leaves abandoned drafts behind. |
| Programmes | `sections/ProgrammesSection.tsx` | There is no `/api/v1/platform/programmes`, which is correct — a programme groups *an institution's* sittings — so the section is left out of the tab strip on the staff surface rather than erroring. |

### Reads the backend does not serve

| What | Where | Today |
|---|---|---|
| A station's version history | `sections/StationDetail.tsx` | There is no `GET …/stations/{id}/versions`, only the writes against one. `StationRead` carries the current version and its content, so the detail screen works on that version and holds whatever `POST …/versions` last returned. It cannot show a history, which is the one thing an author asks for before republishing. |
| One station | `sections/StationsSection.tsx` | No `GET …/stations/{id}` either. The list row is the only source, so opening a station carries the row across rather than re-reading it. |
| Searching or filtering stations | `sections/StationsSection.tsx` | `GET …/stations` takes `cursor` and `limit` and nothing else — no `q`, no exam filter. The old screen's search box is kept and filters the page already loaded (100 rows). Past that it silently searches less than everything, which is the gap. |
| Paging template listings | `api/templates.ts` | `GET …/station-templates` answers a `Page_…` with a `next_cursor` but accepts no `cursor` parameter, so only the first page is reachable. Feedback templates were removed from platform-api; examiner layout lives on `rubric_versions.marking_layout`. |
| What a station is used by | `sections/StationsSection.tsx` | The old delete dialog counted the circuits and slots referencing a station and required a "delete anyway" tick. Nothing answers that question, so the version-level delete has no usage warning. |
| Deleting an exam or a template | `sections/ExamsSection.tsx` | The partner's exam catalogue had a delete. Exams retire and templates only gain versions; neither has a `DELETE`. Retire is offered; delete is not. |
| Importing from the OSCE Guide library | not ported | The institution's screen had "Import from OSCE Guide library", which copied a platform station into the organisation. Platform-owned rows already appear in an organisation's listing (`owner_kind`), but there is no endpoint that copies one, so the modal has no action to call. |

### No backend at all

| What | Old source | Today |
|---|---|---|
| AI-assisted authoring | `b2c/components/shared/aiauto` (~645 lines) and `b2c/components/admin` (~725) | **Served on platform-api.** Template-bound autogenerate uses `structure.generation.profileKey` + per-block `generationHint` / author `placeholder` (profiles from B2C `StationModel` Field descriptions; editable in B2B template builder). `GET /api/v1/station-generation-profiles`. Staff media **Generate** via `/platform/generate/*` (B2C `shared_prompts.py`). B2C Firestore autogenerate and AV pipelines not ported. |

### Ported as fields rather than as a builder

The station-template and feedback-template structures are open JSON objects on
the backend — their shape is the exam's, not the platform's. The retiring
client had a drag-and-drop builder over them (`features/stations/templates`,
~2,700 lines: a component palette, a canvas, a section filmstrip and an
inspector) that only ever wrote what a person could also type. This port edits
those objects as validated JSON, with the parse failure shown under the field
and the commit disabled until it parses. The builder is a real piece of UI and
worth bringing across; it is not a gap in the backend, and nothing is
unreachable without it.

## Peer practice — the marketplace and the paired session

The train shell now mounts `PeerPracticeProvider`: the SSE queue, minimized
indicator, match prompt and joinable booking prompt survive page navigation.
Dashboard and mock completion use `PracticeOptions`; organisation mounting
retains a scoped provider. Queue storage is isolated by user, exam and audience,
restores through the status endpoint, and listens for cross-tab changes. Join
checks for an existing active session before taking another queue place.

Marketplace post/claim success changes tabs, failed posts retain form values,
claim loading stays in the confirmation, and cancelling a booking refreshes the
list. Local date/time rendering and the **10-minute** join window are preserved.
Upcoming prompts refresh every 30 seconds and on focus; queue updates use SSE.

### Session parity implemented

The full-screen runner uses the API's `current_phase` and `phase_ends_at`.
Delayed reads cannot rewind a later phase. Local/remote human camera tracks and
microphone/camera controls replace `AgentTile`, including reconnect and device
error states. Consultation/debrief use the 3/5 video, 2/5 material layout at
large breakpoints. The six-minute warning, consultation time-up prompt,
partner-joined sound, alarm, end confirmation, no-show and abuse reports, rating
and comment feedback, and manual requeue are present. End and feedback failures
remain visible instead of pretending the action succeeded.

Preparation now uses the structured station brief and patient History / ICE &
Concerns / Persona components. The peer API exposes the frozen structured
material, withholding patient information from the doctor until review and
management/teaching until debrief. Waiting and preparation have no call panel;
the human video call connects at consultation. The SSE client resolves the
same-origin proxy URL and handles named snapshot events, keeping both roles on
the server phase. Camera/microphone access requires HTTPS or localhost.

### Backend differences still requiring parity work

| Legacy behavior | Current behavior and remaining work |
|---|---|
| Two-minute match acceptance and decline/requeue | The global prompt counts down 120 seconds; Accept opens the runner. Not now/timeout calls the existing end-session endpoint, closing the immediately paired room. Acceptance and deadline persist across refresh/tabs. This is **not** backend pending acceptance: add a decline/requeue protocol for exact parity and automatic recovery of the other participant. |
| Partner-left versus abandoned reason | The stream exposes ended status, without end actor/reason or live disconnect presence. The UI says the session ended and offers feedback or “Join queue again”; it cannot reliably identify who left or automatically abandon a disconnected peer. |
| Optional rating and “Would practise again?” | Platform requires a 1–5 rating. Although the schema contains `would_practice_again`, the router/service do not save it. The UI submits only the rating/comment the endpoint stores. Feedback currently occupies shared session columns, so per-participant feedback also needs backend work. |
| Recording, transcript and doctor AI feedback poller | Still P-1. No recording/egress, scoring or feedback-result endpoint is available for peer sessions; no AI feedback readiness is invented. |
| Automatic requeue | The completed/ended screen provides manual “Join queue again”. It checks for an active session first. |
| Partner and poster usernames | Current marketplace schemas and cards support supplied usernames. Cards fall back to “A colleague” when absent; the runtime session still exposes only a partner id. |
| Queue join partner-unavailable error | The queue API has no equivalent code. The match prompt detects an ended room and shows “Partner unavailable”; claim conflicts retain the API error in the confirmation modal. |
| Leaderboard | Skipped; already commented out in legacy. |

Browser parity still needs two entitled accounts and configured LiveKit to test
both roles for SCA, PLAB, CASC and Ortho. Automated timing tests cover all four
exam contracts and join boundaries; they do not prove two-way video or backend
match/expiry delivery. The API remains authoritative for entitlement and audience.

## The team and the roster (institution)

The retiring client ran both through one `useOrgTeamPage` hook, and most of
what it did to a *person* was an operation `platform-api` deliberately does not
have. Nothing below is a missing screen; it is a different model, and where the
difference loses something an institution used, it says so.

### Removal is revocation

| What the old screen did | Here |
|---|---|
| **Remove a staff member from the org** (`DELETE` staff, and a bulk "Remove" over a selection) | There is no delete. `POST /memberships/{id}/revoke` revokes — the record of who had access, and when, survives, which is what an examination audit needs. The screens offer Revoke and Restore. |
| **Remove a trainee from the team** (single and bulk) | Likewise `POST /trainees/{id}/access` with `{"revoked": true}`. A trainee has sat things; deleting the row would take an examination's candidate with it. |

If an institution genuinely needs erasure — a person added in error, a data
subject request — it has no route today. That is the one real loss in this
pair and the case for a delete that refuses once anything is attached.

### Passwords and login emails

The whole provisioning apparatus is gone, and deliberately: `POST /memberships`
and `POST /trainees` invite an unknown address, create the account and email a
link to choose a password. So there is no endpoint behind any of these, and
none is wanted:

- a temporary password generated in the browser, shown on the page, and copied
  to the clipboard for an administrator to relay;
- "Email login to all staff", "Send first invites (n)", "New passwords for
  everyone eligible", and the per-row "Send again (new password)";
- the **Portal email** column and its `b2bPortalLoginLastSentAt` stamp — the
  platform has no record of what it has emailed to whom, so the column has
  nothing to show.

One thing does go missing with them: **an administrator cannot re-send an
invitation.** If the first email is lost, there is nothing to press. A
`POST /memberships/{id}/resend-invite` is the smallest fix.

### `GET /memberships` does not carry the email address

`tenancy/service_memberships.list_memberships` builds every row through
`_membership_read(r)` with no `email`, so the field is `null` on the list and
on `PATCH`; only the `POST` response fills it in. The team list therefore
cannot show addresses for people it did not just invite, and says
"Account without a listed address" beside the first eight characters of the
user id rather than printing a uuid as if it were a name. It is a one-line join
in the service, and it is the single thing that would most improve this screen.

**[2026-09-23: served.]** `list_memberships` now reads the page's addresses
through `identity.user_refs_by_ids` — the helper whose own docstring says it is
for read models that show a name beside a row — and the two write routes
(`PATCH` role, revoke/restore) answer through the same join, so a screen no
longer loses the address on the row it has just changed. `POST` still answers
from the lookup it did to do the job at all. `/platform/organizations/{slug}/memberships`
calls the same service and is fixed by the same change. The screen's
"Account without a listed address" fallback stays: it now means the account is
gone, which is the only way the field can be null.

### Cohorts and groups

The platform splits what the old client held in one free-text `cohort` string:
a **cohort** is an intake a trainee belongs to, a **group** is a list you put on
a circuit. That is better, and it costs four operations the old screen had:

| What the old screen did | Here |
|---|---|
| Rename a group (and rewrite every trainee's label to match) | No `PATCH /trainee-groups/{id}`. A group is created and populated; the name is fixed. |
| Delete a group | No `DELETE`. |
| Change a trainee's cohort after they are added, or move a selection into a group in bulk | No `PATCH /trainees/{id}`. A cohort is set when the trainee is created; group membership is edited through `PUT /trainee-groups/{id}/members`, which is the whole list at once. |
| Rename, archive or delete a cohort | Only `GET` and `POST` exist. |

There is also **no endpoint that lists a group's members** — `GroupRead` carries
a count and nothing else. The group editor reads membership with
`POST /roster/resolve` on that one group, which answers exactly the ids a
circuit builder would get. It works and it is honest, but a
`GET /trainee-groups/{id}/members` would be the obvious shape.

The CSV import accepts a `cohort` column and matches it to an existing cohort by
name. An unrecognised name is reported *before* the upload and those rows import
with no cohort, because there is no way to set one afterwards.

### Staff cannot be imported from a spreadsheet

`POST /trainees/bulk` exists; there is no equivalent for memberships, so the old
import's "Trainees or Staff?" step is now trainees only. Staff go in one at a
time.

### Exam access had no screen at all

The entitlement endpoints were among the fifteen nothing called. They have one
now (**Trainees → Exam access**), and two things about it are worth knowing:

- a grant is made against an **email address**, and `EntitlementRead` answers a
  `user_id` — no address, no name. The screen joins it back through
  `Trainee.user_id`, so a grant to somebody who is not on this roster, or who
  has not yet accepted their invitation and therefore has no user row, shows as
  "Not on this roster";
- `live` is the field that gates. The list carries revoked and expired rows too,
  so anything reading "granted" off the row's existence is wrong.

### `trainee_id` means two things, and both are in this pair

Everything in the `roster` slice — access, group members, resolve — takes
`trainees.id`. A circuit slot takes `users.id` (`NewCircuit` sends
`Trainee.user_id`). `POST /roster/resolve` therefore answers **roster** ids, and
whatever eventually wires it into the circuit builder has to map them across
`Trainee.user_id` first — a trainee who has never signed in has no user row and
cannot be put on a circuit at all.

## The live session runner (institution)

The circuit runner came across as one screen over a server-driven circuit,
where the retiring one was two layouts over ninety-four files driving the
examination from a browser. Most of what is not here is not missing — it is
something the backend now does, or deliberately refuses. Both kinds are below,
because a reader comparing the two screens will notice either way.

### No microphone, no camera, no video tiles — and that is the design

The retiring runner gave a supervisor a full LiveKit room: a tile grid, a
camera, and a microphone described in its own copy as "you can coach or
intervene". None of that ports.

- `POST /circuits/{id}/observer-token` mints a **subscribe-only** token — the
  grant carries `can_publish=False`, so there is no microphone to mute and no
  camera to turn off. It is a guarantee rather than a UI state on purpose: a
  candidate must not be promptable mid-consultation, and the transcript has to
  stay a record of what they said to the patient.
- Nothing in this product publishes video. The candidate's own room is voice
  (`VoiceRoom` asks for audio only), and the patient is a voice agent. A tile
  grid here would be a grid of black rectangles, which reads as a broken camera
  rather than as a voice call.

What is here instead is `ObserverPanel`: the server's clock, who is actually in
the room, and who is speaking. The one thing genuinely lost is a supervisor
being able to speak into a training circuit, which the old runner allowed and
this backend does not offer a token for.

### The reading brief is not in the runner

**[2026-09-23: stale — it is in the runner.]** `sessions/SupervisorReadingBrief.tsx` is mounted in `CircuitRunner.tsx` and resolves the active slot's brief for the supervisor, and the candidate has `trainee/SlotReadingBrief.tsx` off the attempt read. This row describes the state before the candidate-scoped brief read landed.

The old runner showed the station's brief in a sidebar while reading time ran.
`CircuitConsole` carries a station's title and version and no content, for the
same reason the station library does not — see "The station library" above. A
candidate-scoped brief read is what this needs.

### Nothing says whether a circuit's feedback has already been published

`POST /orgs/{slug}/circuits/{id}/review/finalize` publishes it and there is no
matching read, so `CircuitFeedbackCard` can say "published" only about a
publish it just did. Reopen the screen and the card offers to publish again as
though it never had. A `GET .../review` returning `CircuitReviewRead` would fix
it in a line.

### A latecomer cannot be given a particular station

The old add-trainee modal picked a station for the person being added.
`POST /circuits/{id}/append-trainees` takes user ids only and the backend pairs
them positionally, so the runner offers the people and not the stations. It is
training-only, too: an exam circuit is one candidate by construction.

### Deliberately dropped, because the server owns it now

- **The timer data channel.** `useCircuitTimerChannel`, `protocol.ts`, the
  supervisor icon bar and the "start reading time / start consultation"
  controls all published the examination's clock from one browser over LiveKit
  data packets. The clock is `phase`, `phase_ends_at` and `remaining_seconds`
  on the console stream now, and the transitions are `start`, `advance` and
  `auto-advance`. Two supervisors with the page open no longer disagree, and a
  refresh no longer loses the timing.
- **Activating a slot from the browser.** Putting somebody on station is
  `jump-to` — a recorded override with a reason — rather than local state.
- **Polling.** The old console re-fetched every eight seconds and resolved each
  station title and candidate name one request at a time.

### Two things the rebuilt console got wrong, now fixed

Worth naming because they were in this repo rather than the old one: it printed
alert **codes** at the supervisor (`no_running_attempt` on screen mid-exam —
the backend sends codes precisely so the client can choose the words), and its
slot badges switched on statuses the backend never sends (`live`, `ended`,
`in_progress`; the real ones are `scheduled`, `reading`, `in_consultation`,
`completed`, `skipped`). Both are in `support.ts` now, with tests.

### `edit-lock` is not this screen's business

`GET /circuits/{id}/edit-lock` stays unwired, and so do `editable` and
`edit_block` on the console frame. They answer whether the circuit's *slots*
can be rebuilt, and `consultation_in_progress` — one of the three codes — is
the normal state of a running examination, so surfacing it here reads as a
warning about nothing. The runner offers no structural edit: adding a latecomer
is `append-trainees`, which the backend gates on the circuit being live and in
training mode instead. The screen that rebuilds a circuit is where this
belongs.

## Results and reviews (institution)

The sitting report carries the whole examination in one request, so most of
what the retiring client assembled by hand — a cohort summary, a candidate
pack per person, a probe per slot — is one screen with disclosures. What
follows is what the backend does not offer, and the handful of places the
rebuilt screens were wrong about it.

### Three things that did not work at all

Named because they were in this repo, not the old one, and each was a silent
failure rather than a visible one:

- **Recording a decision was a POST.** `save_decision` is a **PUT**; the POST
  answered 405 and the screen reported it as a generic failure, so nothing in
  this client had ever recorded a decision.
- **"Borderline" is not an outcome.** `SaveDecision.assessment_outcome` is
  `pass | fail | inconclusive | withheld`. The rebuilt screen offered
  borderline, which 422s — and the two unresolved outcomes it was standing in
  for mean different things: `inconclusive` is "not enough was assessed",
  `withheld` is "decided and not being released".
- **The evidence was never sent.** Release re-checks that the marking a
  decision was signed off against has not moved, by fingerprinting `evidence`
  at sign-off and comparing at release. Sending none made it compare two empty
  objects and pass every time — so a station re-marked between sign-off and
  release would have sent a candidate an outcome nobody approved. The screen
  now sends the candidate's per-station marking, sorted so the same marking
  always hashes the same.

### There is no read for your own slot review

`/orgs/{slug}/slots/{id}/reviews/mine` is a **PUT and nothing else**. The
rebuilt screen called it as a GET, got 405, caught it, and rendered an empty
form — so a reviewer's saved draft never came back and a second visit
overwrote it. `SlotReview` now finds its own review in
`GET /slots/{id}/reviews` by matching `submitted_by` against the signed-in
user. A `GET .../reviews/mine` would make that a direct read; it is a small
thing and it was a real data-loss bug.

### A decision has no optimistic concurrency

`SaveGpLeadReview` takes a `revision` and refuses a stale save — two leads with
the same station open cannot overwrite each other. `SaveDecision` takes no such
field, so two administrators editing the same candidate's decision silently
overwrite one another. Every save is a new revision and nothing is lost from
the record, but the last writer wins and neither is told. The retiring client
sent an `expectedRevision`; there is nothing on this backend to send it to.

### Releasing: no bulk route, and no notification

- Release is one candidate at a time. The screen releases everything signed off
  and not yet out, one request each, and names anyone the backend refuses
  rather than reporting a count that hides them.
- The old bulk release had a **"Notify candidates"** checkbox. Nothing on
  `POST .../decision/release` takes one, and `notifications` is a separate
  slice this screen does not reach into. A released result is visible when the
  candidate next looks.

### No cohort export

The old cohort report had **"Export readout"**, which downloaded the ranking as
markdown. There is no export route. The ranking is also computed per request
here rather than cached, so the old "Refresh ranking" button has nothing to do.

### `recruitment_outcome` is not shown

The decision record carries one, and the backend checks the two outcomes
against each other so a failed candidate cannot be recorded as appointed. It is
deliberately not on this screen: Assess is an examination arm and records an
assessment. The hire arm is a contract, not a separate product — see the ADR —
and whatever renders it is where that field belongs.

### Ranking is exam-only, by design

`GET /sittings/{id}/cohort` answers 422 `not_an_exam_sitting` for a training
one, and the screen treats that as "no ranking here" rather than as a failure.
A training circuit is people practising, and ranking them against each other
would turn practice into an assessment nobody agreed to sit.

### The platform's exam listing is not the platform's prefix

`GET /api/v1/platform/exams` does not exist — that path is POST-only, and the
platform's listing is the unscoped `GET /api/v1/exams`, which returns the
catalogue's drafts to a platform admin and to nobody else. The authoring
capability spells every path as the scope plus a name, so it put a GET on the
POST-only route and the staff console's Exams section showed a 405 instead of
the catalogue. `scripts/smoke.mjs` is what found it.

It is the fourth asymmetry named in `api/scope.ts`, beside programmes, the
brief and version deletion: `examListPath(scope)`. `drafts=true` goes with an
organisation's listing, where it narrows to that institution's own rows; the
platform listing decides by who is asking, so the query is not sent there.

## The institution dashboard and the exam-day board

### "Ready to run" counts an organisation's own stations only

`OrgSetup.stations_authored` is `count_stations(org_id) > 0`, which counts what
this institution has **authored**. An organisation that runs the platform's
catalogue — a legitimate and probably common way to use this — has none of its
own, so `ready_to_run` stays false and the dashboard offers "continue setting
up" to somebody already running examinations. The seeded demo org is exactly
that case.

The screen does not paper over it: the step says the count is of your own
cases, and the tile is labelled "Your stations" rather than "Stations". The fix
is the backend's — either count adopted catalogue stations towards it, or say
`stations_available` and mean it.

### The board has no history

`GET /orgs/{slug}/live` is what is running *now*. There is no "what happened
this morning" — a circuit that has ended leaves the board and is only findable
through its sitting. For an exam-day post-mortem that is the sitting report,
which is a different question asked a different way.

### Nothing links a supervisor to the person who assigned them

`SupervisorCircuitRow` says which circuits this person supervises; there is no
route the other way, so an administrator cannot see who is covering what
without opening each circuit. The live board names the supervisor per running
circuit, which covers the exam-day case and not the planning one.

## The trainee arm and self practice (institution)

`b2b/components/features/{trainee,practice}` — 29 files, 4.1k lines — is now
`domains/assess/trainee` in eight. Most of the reduction is not compression: it
is that the retiring arm answered in the browser several questions the backend
now answers, and had a second, near-identical implementation of the
consultation runner.

### There is no per-sitting read for a candidate

`/me/sittings` carries every sitting *and every slot* this person owns, and it
streams. So the sitting page is a projection of the same feed the overview
renders rather than a second endpoint — which is also why it updates live
without polling, where the retiring detail page re-fetched every five seconds.

A `GET /me/sittings/{id}` would make a deep link cheaper (the page currently
loads everything and filters), but it would be a second source for the same
facts. If one is added it should replace this read rather than sit beside it.

### A candidate cannot read the circuit's published feedback

The retiring arm had a whole screen for it —
`TraineeCircuitFeedbackPage`, reached from a training circuit — reading a
`mergedNotes` document with a contribution per turn.
`POST /orgs/{slug}/circuits/{id}/review/finalize` writes that summary and
**nothing reads it back for the person it is about**: the reviews live under
`/orgs/{slug}/slots/{id}/reviews`, which is an org route, and a trainee's own
`/me/results/{sitting}` carries only the sitting-level outcome and rationale.

So a candidate on a training circuit sees their own station records — the
transcript and the automated marking, both off the attempt — and not what the
supervisor wrote about the circuit. **This is the largest thing J14 could not
port.** The obvious shape is `GET /me/sittings/{id}/circuit-review`, disclosed
on the same rule as a result.

### Nor their own slot review

Same root cause as the entry above and as the one under "Results and reviews":
there is no `reviews/mine` read for the reviewer, and no per-slot read at all
for the candidate. `MySlot.attempt_id` gives them the automated marking, which
is not the same thing as what an examiner recorded.

### Self practice is the organisation's library, sat through `/attempts`

The retiring arm had three doors onto one act — self practice inside a
trainee's workspace, a direct-practice home and its station list for a partner
account — with `selfPractice.ts`, `directPractice.ts` and a `mock/` folder of
its own behind them: a timer, a LiveKit consultation, five tabs and a completion
page. All three list an organisation's published stations and start a solo
consultation on one, so they are now one screen over `capabilities/attempt-runner`.

Two things follow from that:

- **`POST /attempts` takes only `practice` and `self_practice`.** The pattern on
  `CreateAttempt` is `^(practice|self_practice)$`, so the other kinds in
  `AttemptKind` are created by their own routes, not this one. `self_practice`
  has been added to that union — it was missing, which is what the shape
  disagreement noted under "Mocks" is about.
- **The candidate needs an entitlement to the exam.** `start_attempt` calls
  `entitlements.require` whoever is asking, so an institution must have granted
  the trainee access (Trainees → Exam access) before self practice works. That
  is the right gate and it is worth knowing: a rostered trainee with no grant
  gets `not_entitled` at the moment they press a station.

### `GET /orgs/{slug}/stations` hands a trainee the whole station document

**[2026-09-23: shut server-side.]** `stations/service.py`'s `list_stations(..., full_content)` reduces a reader who is not admin or assigned staff through `domain_content.candidate_content`, so the patient material no longer leaves the server. `SelfPractice.readingBrief()` remains but is no longer the only thing standing between a trainee and the answer. Gap-closure-plan Phase 0 S1 and S2 are closed by this; S3 (the `station_not_found` mapping) should be re-checked the same way before being scheduled.

`StationRead.content` is the version's full content — on the seeded case that
is `candidate_brief` **and** `patient_brief` together, and on a
template-authored station it is every block, the hidden ones included. The route
is `OrgReader`, and that predicate admits a trainee (`may_read_org` is
`is_org_admin or is_assigned_staff or is_trainee`), so anybody on the roster can
read the patient's material and the examiner's notes for every station their
organisation has authored — including the ones they are about to be examined on.

`SelfPractice` reads exactly one field out of it, `readingBrief()`, and the
helper says why. That is a client being careful about a response it should not
have been given: the fix is the backend's, either a reader-scoped projection
that carries only the brief, or a `GET /stations/{version}/brief` a candidate
may call. Until then the disclosure is one `fetch` away from anybody signed in
as a trainee, whatever this screen renders.

### The practice mock — selecting stations and running a circuit alone — is not ported

`PracticeMockSetupPage`, `PracticeMockRulesPage`, `PracticeStationRunnerPage`
and `PracticeMockCompletePage` let somebody pick *n* stations from an exam and
sit them back to back with one clock, then review the set. On the platform that
is a **station set** — `/me/station-sets`, which `domains/train/mocks` already
implements — and the institution arm does not mount it today.

Nothing in the backend stops it: station sets are a `/me` resource. Mounting
mocks on Assess is a line in the surface manifest and a route file, and it would
replace those four screens exactly. It was left out of J14 because collapsing an
institution's mock into the consumer one is a product decision, not a port.

### The pre-join states are gone, and that is the point

`TraineeJoinPreJoinStates` had four phases — loading, waiting, ended, error —
with copy chosen by `isSelfLedTraineeSession`, `examSelfLedTimer`,
`isDirectPractice`, `isSoloPractice` and `partnerSelfLedTraining`, five booleans
deciding what a candidate was told about whether they could go in. The backend
answers that with `can_join`, so there is one state and no phase machine.

The join is still automatic during reading, for the reason recorded in
`JoinRoom.tsx`: the patient is dispatched on the server's clock and needs the
room to exist by then.

### No microphone or camera controls for a candidate, either

The same as the supervisor's case recorded under "The live session runner":
nothing in this product publishes video, and `TraineeLiveRoom`'s tiles, device
pickers and the LiveKit timer data channel have no counterpart. The clock is
read from `remaining_seconds` and `phase_ends_at`.

### `domains/train/AttemptResult` and `StationRecord` are the same screen twice

Both render an attempt's marking beside its transcript. They are separate only
because they sit in different arms and a domain may not import another domain;
the parts they compose — `AttemptFeedback`, `TranscriptView` — are shared, so
the duplication is the heading and the layout. The Train one still polls for a
result where `AttemptFeedback` streams; folding it onto the capability would
remove both the duplicate and the poller.

## The staff console

> **2026-09-19.** Most of what follows is closed. `platform-api` now serves
> `GET /platform/audit` (cross-tenant, filtered by org, actor and action),
> `?platform_admin=true` on the account search, contract dates and an
> `at_risk` list on the overview, console membership routes (role, revoke,
> restore), a one-step contract renewal, and the whole support view of an
> account — attempts with their marking state, entitlements, payments, refused
> webhook deliveries, history — with the actions that fix them (rescore,
> salvage, fail, grant/extend/revoke, replay, manual payment, refund) and
> immediate deactivation. `domains/platform` wires all of it: the account's
> Attempts, Entitlements, Billing and History tabs, `/staff/attempts/[id]`,
> `/staff/billing`, `/staff/audit` and `/staff/ops`. See
> `platform-api/docs/SUPPORT-RUNBOOK.md`. **Later that day** the old B2C user
> console came across too: `/staff/users` is the account directory grouped by
> exam (`GET /platform/directory`), and the detail gained Stations (reset
> attempts, delete progress), an Account tab read from facts, and exam date
> and extra reading time on Profile. Still open: the org hierarchy, LLM
> generation keys, and the SSO and contact-inbox screens.


`b2b/components/features/platform` (9 files, 2.3k lines) is now
`domains/platform` (eight files). The overview, the tenant directory, an
organisation's own screen and the user search all came across. Four things did
not, and one of them is a deliberate decision rather than a hole.

### A platform admin cannot read an organisation's members or its audit log

**[2026-09-23: stale.]** `domains/platform/api.ts` calls `GET /platform/organizations/{slug}/memberships` and `…/audit`, and `MembersSection.tsx` / `AuditSection.tsx` render and act on them (role, revoke, restore). The platform-admin routes are the ones the console uses; the org-scoped `/orgs/{slug}/…` reads remain `OrgAdmin`-only, which is the policy the row cites and is unchanged.

The largest gap, and the reason the organisation screen ends with a card saying
so. `GET /orgs/{slug}/memberships` and `GET /orgs/{slug}/audit` are both
`OrgAdmin`, which is declared `allow_platform_admin=False` — on purpose:
"a platform admin may read any organisation for support, but does not thereby
become its administrator", and the legacy policy is emphatic that a console
admin inherits no org powers. So both answer 403 to this console, and the old
`PlatformAuditPage` (filters by org slug and actor email) and the member list
on `PlatformOrganizationDetailPage` have nothing to render.

What the console can still do is seat the **first** member —
`POST /platform/organizations/{slug}/memberships` exists exactly because a new
tenant has nobody to add anybody — so provisioning is not blocked. Changing a
role, revoking one, and reading the log are the organisation's own.

Two ways out, and they are different decisions: open the two reads to a
platform admin (one `allow_platform_admin` on each), or add a
`/platform/audit` that reads across tenants, which is what the retiring console
actually had and what "who suspended this tenant, and when?" needs. The second
is the one worth having; the first would quietly widen `OrgAdmin`'s promise.

`scripts/smoke.mjs` walks both routes and allows either answer, because the
smoke account is a member of the org it switched into and so reads them through
its membership. Against an organisation it does not belong to, both are 403.

### There is no list of platform administrators, and no field saying who is one

**[2026-09-23: stale.]** `GET`/`POST /api/v1/platform/admins` exists and `domains/platform/PlatformTeam.tsx` lists, invites and revokes through it, mounted at `/staff/team`.

`PlatformTeamPage` listed them, granted by email and revoked by id. On
`platform-api`, `PUT /platform/users/{id}/platform-admin` is the whole of it:
there is no listing, and `UserSummary` — the only shape `/platform/users`
answers — carries `id`, `email`, `name` and `created_at`. `is_platform_admin`
exists on `UserRead`, which is `/me` only.

So the grant lives on the user row, and the screen does not pretend to know the
current state: it offers Grant and Revoke as two explicit acts behind a
disclosure, and shows what *this session* just did rather than what is stored.
Adding `is_platform_admin` to `UserSummary` is the one-field fix; a
`?platform_admin=true` filter on the same listing would bring the team screen
back whole.

### An organisation's counts, and its at-risk list

`PlatformDashboardPage` showed active users and sessions over thirty days and a
list of at-risk tenants derived from contract dates;
`PlatformOrganizationDetailPage` showed trainees, sessions, practice users and
memberships-by-role for one tenant. `GET /platform/overview` answers two
integers — `organizations` and `users` — and `OrganizationRead` carries no
stats at all, so none of the six counts survive.

"Needs attention" is therefore the organisations whose status does not permit
signing in, which is servable from the directory and catches the same tenants:
the sweep that suspends a lapsed contract puts them in exactly that state.

### Contract dates are write-only

`UpdateOrganization` takes `contract_starts_at` and `contract_ends_at`, and
they matter — `jobs.py` suspends an organisation whose contract has lapsed.
`OrganizationRead` returns neither, so the form cannot show what is stored and
says so on the screen. It also never sends a blank field, because submitting
one would silently clear a date this console cannot see; clearing is its own
button. Putting the two columns on `OrganizationRead` is the fix.

### Deleting a tenant is gone, and that is the decision

`PlatformTenantDeleteFlow` (319 lines) previewed the cascade — portal users,
memberships, trainees, sessions, circuits, slots, feedback, station instances,
template versions, schemas, exams, cohorts, practice users, entitlements, audit
entries, and any child institutions — and then deleted all of it behind a
type-the-slug confirmation. `platform-api` has no delete, and
`service_platform.py` says why in its own docstring: an organisation's rows
include candidate results, which exist to be defensible months later, and a
cascade would take them. Suspension is the reversible mechanism and it is what
the organisation screen offers. This is not a gap to fill.

### Smaller ones

| What | Where | Today |
|---|---|---|
| Bootstrap admin credentials | `ProvisionPanel.tsx` | The old form took an admin email and a temporary password generated in the browser, displayed it in `TenantAdminProvisioningPanel` for an administrator to relay by hand, and offered "Send login email". There is no bootstrap-admin route and no login-email route; the first member is seated by address and the backend emails a link. No password passes through this app, which is the improvement rather than the loss. |
| Reprovisioning an org's admin | not ported | `b2bReprovisionTenantAdmin` — same absence. Seating another member is the nearest thing, and it does not reset anybody's password. |
| Resetting somebody's password from the console | `domains/platform/UserDetail.tsx` | Wired to `POST /platform/users/{id}/reset-password` when platform-api serves it; otherwise the button fails with the API error. |
| Revoking one person's access to one organisation | not ported | `b2bPlatformRevokeOrgAccess` / `…Restore`. That is `POST /orgs/{slug}/memberships/{id}/revoke`, which is `OrgAdmin` — not on the platform support routes. |
| A user's memberships, last login, and whether they must change their password | `domains/platform/UserDetail.tsx` | Wired to `GET /platform/users/{id}` when served. Search rows show `is_platform_admin` when `UserSummary` carries it. |
| Platform org member list and audit from the console | `OrganizationDetail.tsx` | Wired to `GET /platform/organizations/{slug}/memberships` and `…/audit` when platform-api serves them; org-scoped routes still 403 for a console-only admin. |
| LLM + AV production (staff) | `capabilities/staff-media/MediaDetailScreen.tsx` | Draft text: `POST /api/v1/platform/generate/*`. Summary podcast / slide AV / episode audio: `media_production` (`generate-podcast`, `regenerate-av`, `generate-audio`) via procrastinate — needs `OPENAI_API_KEY`, `CARTESIA_API_KEY`, AWS S3, ffmpeg on workers. B2C Flask pipelines unchanged. |
| Moderation queue | `capabilities/staff-moderation/` | `GET /platform/moderation/posts` — not on every platform-api build yet. |
| Searching or filtering the directory on the backend | `Organizations.tsx` | `GET /platform/organizations` takes `status`, `cursor` and `limit`. The type filter and the search box work over what has been paged in, which is why the whole directory is walked (25 pages of 100). Past that it silently searches less than everything. |
| The organisation hierarchy | `Organizations.tsx` | The old directory showed an institution's parent partner, from `parentOrgId`. `OrganizationRead` has no parent, so a row shows its type and not who it sits under. |
| Filtering the audit log by actor | not ported | Part of the audit gap above. The org-scoped log takes `cursor` and `limit` only, so even where it is readable there is no actor or action filter — `domains/assess/team`'s History tab has the same limit. |

## Help dock parity

The train help dock now uses the B2C article browser (topics, search, categories,
article Markdown, related guides and Back), SCA knowledge-chat suggestions and
conversation, and live voice transcription. Guides use `/api/v1/help/*`, backed
by the versioned B2C help seed rather than the nonexistent legacy Flask routes.
The knowledge chat uses platform summary retrieval and respects the caller's
exam access, including the fourteen-day trial. It requires indexed summary
content and configured OpenAI; live generated answers have not been verified.

Desktop “Guide me on screen” uses the ported B2C screenshot, pointer, progress,
scroll/click RPCs and Guide me / Navigate for me controls. It passes the help
intent and screen-guidance flag through the assistant session extras. The same
UI-guidance feature flag and desktop breakpoint apply. End-to-end voice and
screen guidance still require a configured LiveKit assistant worker. Published
legacy Firestore help changes beyond the seed are not automatically synced.
