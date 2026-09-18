# The system map

Which repository owns what, and what talks to what. This is the part that is currently
tribal knowledge, and the part most likely to send a new engineer to edit the wrong
checkout — two of the directories below are frozen and one of them looks perfectly alive.

Published version: https://claude.ai/artifact/DdGp1umMckFMvBiiMaLPWQ

## Repositories in this workspace

The git root for the APIs is `backend/`, not the workspace root. `assessment-platform/`
and `frontend/` are their own checkouts.

| Path | What it is | Status |
|---|---|---|
| `backend/platform-api` | This backend. FastAPI, SQLAlchemy, Alembic, procrastinate. Replaces both legacy APIs. Branch `feat/platform-api`. | being built |
| `backend/b2b-api` | Legacy institution API, FastAPI + Supabase. Still serving; the source of ported oracles. | legacy |
| `backend/b2c-api` | Legacy consumer API, Flask over Firestore. Still serving; the other oracle source. | legacy |
| `assessment-platform/` | The marking engine and the assessment + assistant LiveKit workers. **All worker changes go here.** | active |
| `livekit/` | **Frozen. Never push to it.** The retired worker project. It still holds the k8s, cluster and Ansible docs, which is why people open it and then edit the wrong thing. | do not touch |
| `frontend/` | Next.js App Router, both b2b and b2c surfaces. Blocked on the four missing read models before it can cut over. | active |

## Services this backend depends on

| Service | Role | |
|---|---|---|
| Postgres | Every table, plus the procrastinate job queue **in the same database** — which is what lets a job be enqueued in the transaction that justifies it. | required |
| Redis | LiveKit Cloud slot counting only. Can be switched off with `REDIS_DISABLED`. Counters are shared with the legacy backends during coexistence, so the numbers must agree. | optional |
| LiveKit Cloud | **The SFU is always Cloud.** Only the agent workers are self-hosted. Cloud concurrency is metered and shared across every product, so past the cap sessions are served from our own workers rather than refused. | required |
| K3s cluster | Runs the self-hosted workers, which is what dodges the Cloud concurrency cap. Deployed from GHCR images — a push to main is the deploy. | required |
| OpenAI + Anthropic | Marking. One default across every exam (`gpt-5-mini` at low effort, falling back to `claude-sonnet-4-5`) rather than b2c's and b2b's differing models producing results nobody can compare. | required |
| Stripe | Checkout and webhooks. The webhook secret is per endpoint; without it deliveries are refused rather than trusted. | required |
| Resend | The only mail provider, and an API key is its only configuration. Everything goes through the `outbound_messages` outbox, never inline. | required |

## Two things that will waste your first week

**LiveKit Cloud showing "Updating", or a worker showing offline, is usually normal.**
It is what a worker recycle looks like from the dashboard. Check the deploy logs, not
the status page — this is a routine non-incident that reads exactly like an outage.

**`railway.toml` is stale.** The workers deploy via GHCR and K3s, not Railway. The
file is still in the tree and is the first thing a new engineer finds when they go
looking for the deployment story. Confirm the current target for `platform-api` itself
with the team before trusting either its `railway.toml` or its `Dockerfile` — that one
has not been verified.
