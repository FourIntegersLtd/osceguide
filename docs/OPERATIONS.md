# Operations: alerts and rollback

Part 3.3 and 3.4 of docs/REGRESSION-PLAN.md. Sentry org `four-integers-ltd-09`
(region de.sentry.io), projects `platform-api`, `platform-web`,
`assessment-workers`. Each project already has Sentry's default "Send a
notification for high priority issues" alert.

## Sentry alerts (configured once, by hand, in Sentry)

Sentry now calls these "Alerts" (workflows) attached to each project's
"Issue Stream" monitor. Production has not reported to Sentry yet (the projects
only know `staging` and `preview`), so the production alerts filter on the
`environment` tag rather than the environment picker. Switch to the picker once
production events arrive. Notify: issue owners, falling back to active members.

| Alert | Projects | Trigger | Filter |
|---|---|---|---|
| Production: new issue | all three | A new issue is created | tag `environment` equals `production` |
| Production: error spike | each, one per app | Metric monitor: number of errors, 1h window, anomaly (or > 3x the 7-day hourly average) | environment `production` |
| Marking gave up | platform-api | New issue, regression, or reappeared | message contains `marking gave up` (api/app/features/attempts/jobs.py) |
| Outbox message abandoned | platform-api | New issue, regression, or reappeared | message contains `message abandoned` (api/app/features/notifications/service.py) |

The last two depend on `log.exception`/`log.error` reaching Sentry through its
logging integration, which happens when `SENTRY_DSN` is set on the api.

## Exam freeze (promote workflows)

`Promote api`, `Promote web` and `Promote workers to production` run the shared `.github/actions/exam-freeze` action (after main's checkout, before
any gate, and again in the job that pushes, because an approval can come hours after the check). It reads the list `WINDOWS` in `.github/actions/exam-freeze/action.yml` (hard-coded; edit that file and merge to add a freeze): comma-separated `start/end` pairs in ISO UTC, for example
`2026-12-03T07:00:00Z/2026-12-03T18:00:00Z,2026-12-10T07:00:00Z/2026-12-10T18:00:00Z`. While now falls
inside a window the run fails and production is untouched. An empty `WINDOWS` value means no freeze. A
malformed entry fails the run rather than being skipped.

To promote during a window (a fix for the exam itself), run the workflow with `override_freeze_reason`
filled in. The reason is written to the run log as a warning. A rollback follows the same rule: typing a
reason is the only way through. Add the windows when a sitting is booked and remove them afterwards.

## Rollback in one step

Roll back first, investigate second. Each path below reuses an artifact that
already ran, so nothing is rebuilt.

| App | How |
|---|---|
| api (Railway) | Railway dashboard, platform-api production service, Deployments: pick the previous successful deployment, "Redeploy". Or `railway redeploy` against that deployment with the CLI. Migrations are not reversed: if the bad release ran one, check it is backward compatible before rolling back, otherwise `poetry run alembic downgrade -1` first. |
| web (Vercel) | Vercel dashboard, platform-web, Deployments: the previous production deployment, "Instant Rollback". Or `vercel rollback <deployment-url>`. Re-enable auto-assignment of production domains once the fix is promoted. |
| workers (K3s) | GitHub Actions, "Promote workers to production", tick `rollback` and set `commit_sha` to the commit production ran before. The pods' `osceguide.io/commit` annotation shows what is running. |

After any rollback: check `/health` reports the expected commit, sign in, open
the dashboard, and write a row in the incident's issue saying what was rolled
back and why.

## Exam-day production readiness (human checks)

These are not enforced in CI; tick them before the first real sitting on the merged exam-day stack.

| Check | Where |
|---|---|
| Staging deploy watched after merge | Railway staging `platform-api` / `platform-worker` deployments; Vercel preview for any `web/` touch |
| Railway replicas, health check path, PgBouncer (`DATABASE_PGBOUNCER=true`), scoring worker (`WORKER_EXCLUDE_QUEUES=scoring` on a second worker service) | Railway dashboard; `api/docs/ENVIRONMENT.md` |
| LiveKit seat limits and agent namespace per environment | Railway `LIVEKIT_*`; K3s worker seats via `infra/ansible/` |
| OpenAI / Anthropic marking tier and rate | Provider dashboards; `MARKING_*` on Railway |
| Resend rate vs `OUTBOX_SEND_CONCURRENCY` | Resend dashboard; `api/docs/ENVIRONMENT.md` |
| Sentry production alerts (see table above) | de.sentry.io |
| Backup restore drill into a scratch DB | `web/docs/BACKLOG.md` E-12; `api/docs/SUPPORT-RUNBOOK.md` |
| Exam freeze windows before promote | Edit `WINDOWS` in `.github/actions/exam-freeze/action.yml` |
| Vercel live board/console stream under load | Browser against staging with SSE open while worker stopped (alerts should refresh on heartbeat) |
| Reviews on the shipped diff | `quality-reviewer`, `reviewer`, `/security-review` when auth/money touched |
