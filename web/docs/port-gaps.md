# Port gaps

Screens that came across from `frontend/` whose backend `platform-api` does not
serve yet, and the handful of places where the two systems disagree about a
shape. One file so the backlog is countable rather than scattered through
`TODO` comments nobody greps for.

Each entry says what the screen does today, so nothing is silently dropped.

## No endpoint on platform-api

| What | Where | Today |
|---|---|---|
| Landing statistics band | `domains/marketing/Numbers.tsx` | The retiring backend served `/api/v1/landing`. `fetchLandingStats` returns `null` without asking, and the band hides itself — asking would 404 on every view of the busiest public page. Putting it back is that function's body. |
| Achievements | `capabilities/account/Achievements.tsx` | **Ported as its own empty state, and it asks for nothing.** The old screen counted station badges from `user.station_progress` and computed streaks in the browser from the transcript list; `platform-api` has neither — progress is attempts, and a streak exists nowhere on the backend. The component takes the four numbers as props and defaults them to zero, so the day something serves them it is a one-line change at the call site rather than a port. It has no route: see "Route files the account capability still needs". |
| Messages / contact | not yet ported | `/messages` in the old arm. No backend. |
| Product feedback form | `domains/marketing` section, unlisted | The "Help Us Improve" landing section is kept but left out of `landingSections`; it needs a product-feedback slice. |
| Push notifications | not ported | `web-push` is deliberately not a dependency here yet. |
| SSO configuration | not ported | `getSsoConfig` in the old arm. |
| Public user profiles | not ported | `/users/[userId]`. The old `b2c/components/shared/users` was not a public profile at all: it is an **administrator's** user list and user detail — plan editing, station-progress resetting, hard delete, filters by plan type. None of it is servable. See "The old `users/` folder" below. |
| Blog authoring | not ported | Reading is `capabilities/media`; authoring has no endpoint. |
| Public blog listing | `domains/marketing/support/landingBlogs.ts` | `GET /media` requires a bearer token, so a signed-out visitor cannot read the landing's blog rail. It hides itself. A public listing — or an anonymous read for published items — would bring it back. |
| Exam wishes | `capabilities/account/ExamWishes.tsx` | Ported, and nothing renders it. It was shown in the week of somebody's exam, and `UserRead` carries no `exam_date` — the same gap the dashboard countdown hits. |
| Accessibility settings (extra reading time) | `foundation/ui/Timer.tsx` | The old client read `accessibility.needs_extra_reading_time` off the user and extended the clock from inside the timer. No such field on `platform-api`. The timer takes the duration it is given; when the field exists, whoever creates the attempt applies it. |
| Photo upload | `foundation/ui/PhotoUpload.tsx` | Posted to the old backend's `/api/upload_photos/{id}`. The component takes an `upload` function now, and nothing supplies one yet. |

## The station library

Five things the retiring station screens did that `platform-api` has no answer
for. The first is a decision rather than an omission and the rest are holes.

| What | Where | Today |
|---|---|---|
| The candidate brief, patient information and management plan | `capabilities/stations/StationDetail.tsx` | `LibraryStationRead` carries no `content` **on purpose**: the library is browsable by every signed-in user, and the content is the brief, the examiner's context and the marking guidance — reading it before sitting the station is reading the answers. The attempt is frozen server-side and the worker fetches it by id, so the scenario never travels through the browser at all. The old client's "Reading time" and "Management" tabs (`user/ManagementScreen.tsx`, the four `*DoctorScreen`s) therefore have nothing to render and are not ported. `AttemptRunner` already takes a `brief` and shows it during the reading phase; the day a candidate-scoped brief read exists, that prop is where it lands. |
| `GET /api/v1/stations/{station_id}` | `findLibraryStation` in `capabilities/stations/api.ts` | There is no per-station read for a learner — every one of them is an authoring route under `/orgs/{slug}/…` or `/platform/…`, gated on permissions a candidate does not have. A station opened by link is found by walking the browse list, bounded at twenty pages. It works and it is cheap, because a row is a title and two ids, but a shared link to a station beyond that is a "we could not find that station". |
| Searching the library | `useStationLibrary.ts` | `browse_library` takes `exam_code`, `cursor` and `limit`. The search box filters what has been paged in, which is why "Load more" stays offered while a term is typed. A `q` on the endpoint would make it a real search. |
| Flagging a station | not ported | The old detail screen had a flag button posting to `/api/flag_station`, which put a station in front of the content team. There is no equivalent, and no `flagged_stations` on `/me`. |
| Attempts used, out of the exam's limit | not ported | The old header read `ALLOWED_STATION_ATTEMPTS` against `user.station_progress`. `ExamRead.station_attempt_limit` is the numerator's half; nothing serves how many of them a person has used on a given station, so the counter is left off rather than shown wrong. |
| Live marking during a consultation | not ported | `live/LiveCoveragePanel.tsx` and `LiveCoverageFeed.tsx` subscribed to `/api/live-coverage-stream` and showed competencies as they were covered. `GET /api/v1/attempts/{id}/stream` pushes `AttemptRead` snapshots until the attempt is marked — the right stream, without the coverage frames. Adding a `coverage` event to it is what this needs; the feed is worth bringing back, because it is the one thing in the old runner people asked for by name. |

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

### There is no active exam on the session

The old client got its exam from the subdomain — `sca.osceguide.com` set an
`appType` in a context, and each exam had its own build of the same screen.
The platform has one workspace and no such field, so `domains/train/dashboard`
derives the list from what the person has actually attempted, been granted or
built a mock for, orders it by attempts, and offers a picker in the header when
there is more than one. Somebody with a single exam never sees the control.
A remembered choice — on the user, or in the workspace — would be an
improvement, not a correction.

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

**No attempt history.** There is no `GET /me/attempts`. The only list of a
person's attempts is `recent_attempts` on `GET /me/dashboard`, and it is
capped at ten with no cursor, so `capabilities/transcripts` shows the last ten
consultations and nothing older. The retiring screen listed one station's
transcripts from a query string, so this is more than it had — but a paged
`/me/attempts` is what the Transcripts page actually wants, and the same
endpoint would answer "my feedback history" for the mocks screens.

**A transcript row carries no station.** `RecentAttempt` has an exam code, a
kind, a status and a date, but not the station's title, so the list reads
`SCA · Mock station` where the old one read the station's name. Every row
would otherwise need its own `/attempts/{id}` and then a station-version read.

**Debriefs are readable only through the tutor's memory.** There is no
`GET /debriefs/{id}` and no debriefs collection: `DebriefSummaryRead` reaches a
client only inside `GET /me/tutor-memory`, so `DebriefDetail` reads the list
and finds its id in it. Two consequences worth stating — a debrief page costs
the whole memory, and the route is `/me/…`, so an examiner cannot read a
trainee's debrief even though the debrief capability is mounted on Assess. A
`GET /attempts/{id}/debrief` keyed on the attempt, with the same visibility
rule the result already has, would fix both.

**A debrief needs a station set.** `POST /me/station-sets/{set}/entries/{entry}/debriefs`
is the only way to start one, so a free-practice attempt — the kind a consumer
makes from the station library — cannot be debriefed at all. The backend
already keys a debrief on `source_attempt_id`; a `POST /attempts/{id}/debriefs`
would make the button work everywhere the feedback does.

**An examiner cannot yet read a candidate's attempt.** `FeedbackView`,
`AttemptFeedback` and `TranscriptView` ask nothing about who is reading — that
is the point of them being capabilities — but `GET /attempts/{id}/result` and
`/transcript` are owner-or-platform-admin (`service_reads._ensure_visible`),
and the reviews slice has no transcript read of its own. So the screens are
ready for the examiner and the endpoint is not: a GP lead reviewing a slot can
see their org's reviews but not the machine's mark or the words that produced
it. Widening the visibility rule to a member of the organisation the attempt's
slot belongs to is the whole of it.

**"Practice as Patient" is not a debrief.** The retiring debrief modal offered
a second choice beside the debrief: run the same case from the patient's side
with the tutor as the doctor. On the platform that is a practice session
(`/me/practice-sessions`), not a debrief, so it belongs with peer practice
rather than in `capabilities/debrief`. Nothing mounts it yet.

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
| Ortho CV upload and display | `Profile.tsx`, `/api/ortho/cv_status` | An exam-specific attachment on a consumer profile. No endpoint. |

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
| `src/app/billing/complete/page.tsx` | `PaymentReturn` | The backend hardcodes `success_url = {FRONTEND_URL}/billing/complete?session_id=…` in `billing/service_checkout.py`. **Not** `/payments/success`, which is what the retiring client used. |
| `src/app/pricing/page.tsx` | `CheckoutCancelled` | The same file hardcodes `cancel_url = {FRONTEND_URL}/pricing`. **Not** `/payments/cancel`. Either these two route files are added, or the backend's two URLs are changed to match whatever is preferred — but they have to agree, or a paying customer lands on a 404. |
| `src/app/app/[workspace]/achievements/page.tsx` | `Achievements` | The old `/achievements` route. |
| `src/app/staff/settings/page.tsx` | `Settings` | The staff console is outside the workspace grammar and has its own route tree, so `surfaces: ["…", "platform"]` on the capability does not reach it — `/staff/settings` is a 404 today. `surfaces/platform/surface.ts` also builds its nav by hand rather than from the capability registry, so the entry has to be added there too. |

### The old `users/` folder is the staff console, not an account screen

`b2c/components/shared/users` (1,395 lines) is an administrator looking at
somebody else: a filterable list with plan-type facets and bulk hard delete,
and a detail screen that edits another person's plan dates, flips `has_paid`,
resets individual station progress and deletes stations from their history.

None of that is an account capability — a capability may not know it is
standing in the staff arm, and this screen is *only* ever the staff arm. It is
also almost entirely unservable: `platform-api` has `GET /platform/users` and
`PUT /platform/users/{id}/platform-admin` and nothing else. There is no
per-user read, no plan write, no progress reset, no delete. It belongs to **J15
(staff console)** with the endpoints it needs, and is recorded here so it is
not mistaken for something J8 dropped.

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
| Paging the two template listings | `api/templates.ts` | `GET …/station-templates` and `…/feedback-templates` answer a `Page_…` with a `next_cursor` but accept no `cursor` parameter, so only the first page is reachable. |
| What a station is used by | `sections/StationsSection.tsx` | The old delete dialog counted the circuits and slots referencing a station and required a "delete anyway" tick. Nothing answers that question, so the version-level delete has no usage warning. |
| Deleting an exam or a template | `sections/ExamsSection.tsx` | The partner's exam catalogue had a delete. Exams retire and templates only gain versions; neither has a `DELETE`. Retire is offered; delete is not. |
| Importing from the OSCE Guide library | not ported | The institution's screen had "Import from OSCE Guide library", which copied a platform station into the organisation. Platform-owned rows already appear in an organisation's listing (`owner_kind`), but there is no endpoint that copies one, so the modal has no action to call. |

### No backend at all

| What | Old source | Today |
|---|---|---|
| AI-assisted authoring | `b2c/components/shared/aiauto` (~645 lines) and `b2c/components/admin` (~725) | The platform admin's four generators — auto station, auto summary, auto blog, auto slide — and the "Generate with AI" tab in the station create modal. `platform-api` has no generation endpoint of any kind, so none of it is ported and the create dialog offers the manual half only. This is the whole of the old `/admin` section apart from the partner dashboard, which is `domains/partner`. |

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

`b2c/components/shared/{marketplace,human-practice}` (41 files, 7.2k lines) is
now `capabilities/peer-practice`. The queue half is whole: joining, the live
pairing stream, the match, the room and ending a session all go through
`platform-api`. The marketplace half stops one step short of the call, and the
session itself has nothing to read during it. Both are backend work, not
frontend work, and neither is a guess — the routes simply do not exist.

### No way into an arranged session's room

`POST /api/v1/me/peer-sessions/{id}/join` validates the ten-minute window and
answers with the session, and `marketplace/service.py` has written
`peer_sessions.room_name` since the slice landed — but nothing mints a token
for that room. The queue half has exactly this route
(`/me/practice-sessions/{id}/voice-token`), added for the same reason: two
people were being paired and had nowhere to meet.

Today **Join Session** checks the person in and says so, and points them at
Live Practice for a room they can actually enter. A
`POST /me/peer-sessions/{id}/voice-token` alongside the one `peer_practice`
already has is the whole of the fix.

### The session has no station

`PracticeSessionRead` carries an exam code, a role, a room and two timestamps.
It does not carry the station the pair are practising, so four screens from the
old runner have no content to render and are not ported:

| What it showed | Needed |
|---|---|
| The doctor's reading brief (per-exam screens) | A station on the practice session |
| The patient's roleplay script — history, ICE, persona | The same |
| The debrief's management plan | The same |
| The station name in the session header | The same |

The pairing job picks no station at all, so this starts further back than the
schema: `peer_practice` would have to choose one when it makes the pair, the
way `attempts` freezes a scenario when it creates an attempt.

### No phase clock

The retiring runner ran reading, consultation and debrief off a single
`preparation_started_at`, recomputing all three phases inside a one-second
interval — the browser deciding when an exam ends. `platform-api` owns
`started_at` and `ended_at` for a practice session and nothing between them.

The session screen shows **elapsed** time, which is true, rather than a
countdown nobody is keeping. `phase_ends_at` and `remaining_seconds` on a
practice session — the columns `sittings` already has — would give this the
server-owned clock the rest of the product uses.

### Smaller ones, each a route that does not exist

| What the old screen did | Today |
|---|---|
| Session feedback after a peer session (would you practise again, 1–5 stars, free text) | Not ported. No endpoint. It fed the matcher's reputation signal. |
| Report a no-show while waiting for a partner | Not ported. |
| Report abuse or harassment during a session | Not ported — and this one is a safety control, so it is the first of these worth building. |
| Requeue after a partner leaves or declines | Not ported. The person leaves the session and joins the queue again. |
| Cancel an arranged session | The card's **Cancel** explains that it is not available and points at withdrawing the slot. `DELETE /marketplace/slots/{id}` covers the poster; the claimer has nothing. |
| Accept or decline a match within two minutes | Not ported. `peer_practice` pairs both people directly, so there is no offer to answer — which also removes the auto-decline, the cancelled-session modal and the localStorage keys the old client kept per exam. |
| Queue expiry after ten minutes | Queue entries are `waiting`, `matched` or `left`; nothing expires them, so the "No Match Found" modal has no event to fire on. |
| The leaderboard by sessions completed | Not ported. Already commented out in the retiring screen. |
| Consultation recording and transcript (`start-egress`, `consultation-ended`) | Not ported — `peer_practice/README.md` names it as open question P-1. |

### Shape disagreements

| What | How it is handled |
|---|---|
| Partner and poster names | `PostRead` and `PeerSessionRead` carry user **ids**, not usernames, and there is no public profile endpoint. Every `@username` in the old cards reads "You" or "A colleague". Two ids on a card are not worth a join; a display name on these two shapes is. |
| A slot was a calendar date plus a wall-clock time plus a timezone | It is one `starts_at` instant, rendered in the reader's own zone. This fixes a real bug rather than losing anything: a slot offered at 19:00 in London read as 19:00 in Lagos. |
| The join window | The old card said twenty minutes and the new backend opens the session at ten (`marketplace/domain.py`). The copy says ten, so the button does not 409 on a person who believed it. |
| Exam and session length | The old app was one exam per deployment and a fixed thirty minutes. Both are asked for now, because a slot and a queue place are addressed to an exam. |
| The partner's tile | `foundation/livekit`'s `AgentTile` reads `useVoiceAssistant`, which is an agent's state. A human partner renders in it but its status line is about an agent that is not there. A participant tile beside it in `foundation/livekit` is the fix, and it is foundation work rather than this capability's. |

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
