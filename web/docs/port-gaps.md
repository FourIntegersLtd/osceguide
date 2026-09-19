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
| Achievements | not yet ported | The old consumer arm had `/achievements`. No backend. |
| Messages / contact | not yet ported | `/messages` in the old arm. No backend. |
| Product feedback form | `domains/marketing` section, unlisted | The "Help Us Improve" landing section is kept but left out of `landingSections`; it needs a product-feedback slice. |
| Push notifications | not ported | `web-push` is deliberately not a dependency here yet. |
| SSO configuration | not ported | `getSsoConfig` in the old arm. |
| Public user profiles | not ported | `/users/[userId]`. |
| Blog authoring | not ported | Reading is `capabilities/media`; authoring has no endpoint. |
| Public blog listing | `domains/marketing/support/landingBlogs.ts` | `GET /media` requires a bearer token, so a signed-out visitor cannot read the landing's blog rail. It hides itself. A public listing — or an anonymous read for published items — would bring it back. |
| Exam wishes | not ported | `ExamWishes` in the old achievements folder. |
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
| Deleting a session | `domains/train/mocks/MockSessions.tsx` | The old card had a bin next to its title (`DELETE /api/delete_mock/{mock}/{user}`). There is no `DELETE /me/station-sets/{id}`, so the card has no bin. A session is cheap and locks rather than disappearing when access lapses, so this is the least painful of the six — but somebody with fifty sessions has no way to tidy them. |
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
| `AttemptKind` in `attempt-runner/api.ts` | `capabilities/attempt-runner` | The client spells the kinds `set_entry`, `slot`, `self_practice`… where the backend's `attempts.Kind` is `set_station`, `exam_slot`, `self_practice`, `practice`, `debrief`, `peer`. Only `practice`, `debrief` and `peer` agree. `capabilities/transcripts/api.ts` labels attempts from the backend's spelling. |
| `user.user_id`, `user.station_progress` | `domains/marketing/InstallPrompt.tsx` | The old consumer user object inlined a progress array. The platform's `/me` carries neither — progress is its own endpoint. The prompt passes `user.id` and a count of 0, which errs towards showing onboarding once more rather than never. |

## Deliberately not ported

- `confetti-check`, a developer scratch page.
- `features/[featureId]`, superseded by the landing's feature sections.
- The four separate B2B console logins (`b2bLoginRoutes`), replaced by the one
  sign-in the platform actually has.
