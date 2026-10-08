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
