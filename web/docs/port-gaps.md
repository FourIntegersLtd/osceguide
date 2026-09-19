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

Until then the consumer dashboard shows what is true: progress, recent
attempts, sets and access.

## Shape disagreements

| What | Where | How it is handled |
|---|---|---|
| `user.user_id`, `user.station_progress` | `domains/marketing/InstallPrompt.tsx` | The old consumer user object inlined a progress array. The platform's `/me` carries neither — progress is its own endpoint. The prompt passes `user.id` and a count of 0, which errs towards showing onboarding once more rather than never. |

## Deliberately not ported

- `confetti-check`, a developer scratch page.
- `features/[featureId]`, superseded by the landing's feature sections.
- The four separate B2B console logins (`b2bLoginRoutes`), replaced by the one
  sign-in the platform actually has.
