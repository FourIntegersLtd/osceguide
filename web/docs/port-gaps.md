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
| Exam wishes | not ported | `ExamWishes` in the old achievements folder. |

## Shape disagreements

| What | Where | How it is handled |
|---|---|---|
| `user.user_id`, `user.station_progress` | `domains/marketing/InstallPrompt.tsx` | The old consumer user object inlined a progress array. The platform's `/me` carries neither — progress is its own endpoint. The prompt passes `user.id` and a count of 0, which errs towards showing onboarding once more rather than never. |

## Deliberately not ported

- `confetti-check`, a developer scratch page.
- `features/[featureId]`, superseded by the landing's feature sections.
- The four separate B2B console logins (`b2bLoginRoutes`), replaced by the one
  sign-in the platform actually has.
